# HE-Austenite paired-property observations

`h2physics.data.embrittlement` provides a bounded Python profile for Muhammad
Faizan's [HE-Austenite compilation](https://doi.org/10.5281/zenodo.23107780), pinned
Zenodo record23107780. Repository metadata and `LICENSE-DATA.txt` identify the
data as [CC BY4.0](https://creativecommons.org/licenses/by/4.0/); source code is
separately MIT. The host neither executes nor copies that source code. The
compilation's license does not establish redistribution rights in every
underlying publication table. Raw data, normalized observations, publication
content and detailed audit JSON remain ignored and excluded from distributions.

The acquired scope is9 of23 listed attachments: the main CSV, composition CSV,
record/composition mapping, workbook, data license, requirements and three
documentation files. Fourteen programs/figures/other assets, including the raw
record JSON, were deliberately omitted from acquisition. This profile audits
all9 acquired files; it does not claim to have read all23 publisher assets or
independently re-extracted the underlying papers. No further acquisition is
required to reproduce the implemented views.

## Direct Python use

```python
from pathlib import Path
import tomllib
from h2physics.data import EmbrittlementCollection
from h2physics.data.embrittlement import paired_property_check

receipt = tomllib.loads(Path("research/data/austenite-embrittlement.toml").read_text("utf-8"))
with EmbrittlementCollection.from_receipt(
    "data/raw/austenite-embrittlement/23107780", receipt,
) as source:
    for block in source.iter_blocks(
        "reduction of area", reference_environment="air", block_rows=32,
    ):
        observations = block.observations
        records = block.records
        same_export_arithmetic = paired_property_check(block)
        # Every record retains raw material/test/environment/notes and source IDs.
```

`EmbrittlementCollection.from_receipt(data_directory, receipt)` is the shorter
alternative when an application already has the parsed TOML mapping. It checks the
dataset DOI, version, rights flag, complete acquired-file set and each SHA-256 against
the code-pinned version manifest before creating the collection. The application remains
responsible for receipt parsing and selecting an explicit external data directory; the
library does not fetch files or infer paths.

Each immutable `EmbrittlementRecord` retains all45 original cells, original
record ID, reported bibliography ID, CSV logical row and physical line span,
file SHA and source identity. A compilation row represents a reported condition
and property. It is not a specimen, an independent replicate or a sampled point
on a stress–strain curve. Record IDs include both source location and author ID;
identities survive property selection, filtering, block partition and missing
values. Quoted multiline CSV records retain their physical line spans.

`iter_blocks` requires one of the five reported property definitions and returns
common immutable `ObservationTable` arrays with23 numeric columns.
SI names such as `exposure_pressure_pa`, `charging_duration_s` and
`Cr_mass_fraction_primary` distinguish converted values from original units.
`block.numeric_source_fields` maps each observation column back to its original
CSV field; `record.fields` always retains the original text and header identity.
Each `EmbrittlementBlock` verifies that source records, observation row identities,
numeric columns and invalid-reason masks retain the same order and shape.
Optional exact
filters select `reference_environment`, `zone` and `hydrogen_exposure`. The paired
reference is **not always air**: helium, nitrogen, argon and uncharged controls
remain distinct in each record's original context. No gas-reference conversion,
baseline substitution or test-condition harmonization is performed. The caller
must use the records' actual material and environment covariates in a comparison.

## Units, roles and missing observations

Reduction of area and elongation percent values are scaled by.01 to distinct
dimensionless quantities. Tensile and notched tensile strengths are separate
quantities in Pa, converted from the source MPa. The four plastic-strain-to-failure
records retain `source_unit_unresolved` for absolute values: the dictionary's
generic `% or MPa` label does not resolve their strain definition. Their paired
dimensionless ratios remain usable without choosing an absolute strain scale.
Do not borrow the percent scale from elongation or interpret them as fracture
toughness, a constitutive damage variable or a verified local fracture strain.

The source gas-exposure pressure is scaled MPa→Pa as
`reported_exposure_pressure`; its absolute/gauge, total/partial and H₂-purity bases
remain unresolved. A precharging pressure is not automatically the mechanical
test pressure. Gas mixture exposure and pure H₂ must not be conflated. One
pressure is explicitly identified by the compilation as a range midpoint; its
derived role survives. No pressure is admitted directly to an EOS/fugacity law.
Gas spin is unresolved; metal hydrogen content does not establish molecular H₂.

Hydrogen wt ppm is scaled by1e-6 to a reported material hydrogen mass fraction,
with total/diffusible/trapped and analytical definitions unresolved. Charging
hours become seconds as a duration, not a recorder/test clock. Reported nominal
strain rate keeps1/s; local/plastic rate and loading-control equivalence are not
inferred. The K temperature field is kept directly and the separate C field is
converted with273.15. Their disagreement is recorded, never silently repaired.
Charging temperature, cooldown/aging, notch geometry and fracture descriptions
remain in original context; they are not invented as structured measurements.

Composition wt% becomes mass fraction. Missing elements remain masked even when
the source lists zero-element assumptions for a derived index. Ferrite number
is an index, not ferrite volume fraction. Nickel-equivalent values remain weighted
composition indices; they are not nickel concentration. The empirical Md30 field
is a separate calculated temperature index, not measured test temperature or a
phase-stability result. No index expression or fracture law is fitted here.

All numeric observations are explicitly literature-reconstructed compilation
records, not newly qualified raw measurements. Absolute plastic-strain units and
the source-labelled `ni_equivalent_reported` provenance remain unresolved.
`numeric_role(field)` distinguishes extracted values, ratios reconstructed from
absolute pairs, derived ratios without pairs and the source-reported ratio-only
case. The `derived`, `derived_assumptions` and `verified` cells are preserved;
the curator's verification flag is not host independent experimental validation.

Blanks and placeholders have distinct invalid reasons. Nonfinite values and
unit-conversion overflow are masked, with the raw reported cell retained.
Negative physical fields survive numerically with an invalid mask; they are not
clipped or dropped. Ratios above1 are not clipped to a loss-only range. Source
band labels are retained as categorical metadata, not engineering acceptance
criteria. `as_time_series()` rejects this non-time dataset.

## Two composition representations and dependence

The source has31 explicit composition keys and102 record-to-composition links.
`record.linked_composition` and `record.composition_mapping` preserve their own
original rows/SHA. `source.composition_observations(linked_row)` exposes the linked
composition as a separate common `ObservationTable`. `record.material_group_id`
identifies the author's shared composition group, including a heat, weld deposit
or filler. It does not manufacture a specimen ID or prove that every linked row
is a separate material experiment.

Main CSV and linked compositions disagree in40 element cells across15 records.
`composition_discrepancies` retains both originals and the field identities.
Neither representation overwrites the other. Nominal and heat-analysis labels
are preserved rather than promoted to measured specimen composition. Weld
deposit/filler chemistry is not silently diluted into parent plate chemistry;
whole-joint observations are not treated as weld-metal-only or base-metal-only.

The collection includes handbook/technical-reference reprints and an explicitly
identified reused measurement. A source ID is a bibliography label, not proof
of independent experimental origin. All default `experiment_ids` therefore use
one dependent-compilation group. A random row/property/material/source split
cannot establish a held-out validation set. An evidenced original-experiment
crosswalk is needed before repartitioning, including across source publications.

`paired_property_check` compares stored H₂/reference values against the stored
ratio, retaining masks, signed residuals and row IDs. The default tolerance.002
is a declared arithmetic audit budget from the compilation, not a measurement
uncertainty. Ratio-only records stay unavailable for this check. Recomputing a
ratio from its own inputs is not an independent physical/model validation. Its
result object validates row alignment, residual arithmetic and the tolerance flags
before another Python consumer can use them.

The deferred cluster cases `austenite-observation-provenance` and
`austenite-observation-contract-integrity` use the existing `fracture-fatigue`
profile. Because acquired source files remain external to the repository, set
`H2_DATA_AUSTENITE_ROOT` in that profile's cluster setup to the absolute directory
containing the pinned 23107780 files. These cases check source/schema custody and
Python result contracts, including missing-path rejection and the exact DOI/record
version; they do not validate a material law or compare independent experiments.
They are planned only and have not run.

## Full-source replay and limits

```powershell
.venv\Scripts\python -m pytest tests/test_embrittlement_data.py tests/test_observations.py -q
.venv\Scripts\python -X utf8 scripts/check_embrittlement_data.py
```

The script verifies receipt/metadata/data license, every acquired SHA and publisher
MD5, all three CSVs, all workbook ZIP members and all six sheets. It compares the
first45 workbook Data columns with the CSV and separately retains every formula
and cached-value status. It never evaluates formulas. The47-column workbook's
last two figure helpers and Summary formulas are derived display fields, not new
measurements. All257 formulas lack cached values in this source version.

The constructor defaults to a2MB per-file cap,5000 data rows per CSV and32768
characters per field. Blocks are1–512 records. Workbook replay additionally
limits expanded ZIP size to5MB, member count100, per-member size1MB, worksheet
rows5000 and columns64; unsafe paths, links and macros are rejected. CSV reading
uses the native Python parser; workbook reading lazily uses optional openpyxl
from the existing data extras. Common hashing, observation objects and masks are
reused. No source program or macro is executed, and source hashes are rechecked.

See [the qualification report](../research/embrittlement_data.md) for exact counts,
source discrepancies and final fingerprints. The usable level is conditioned
comparison of reported paired properties and material descriptors. It supplies
no stress–strain history, fatigue/crack-growth/toughness law, transport/trapping
calibration, fracture-mode model, sigma, certified design threshold or independent
material/facility validation. A source-qualified mechanical model still needs
specimen/heat identity, loading/notch geometry, environmental/charging boundaries,
material microstructure, uncertainty and independent original experiments.

Each EmbrittlementBlock is now issued only by EmbrittlementCollection.iter_blocks().
The block seals observation content, source-row and linked-composition identities,
and invalid-reason metadata; paired_property_check() revalidates that receipt before
using it. The existing deferred observation contract covers direct construction,
token-reuse cloning and post-issuance mutation. This is data-lineage protection only,
not a material law or independent embrittlement validation.
