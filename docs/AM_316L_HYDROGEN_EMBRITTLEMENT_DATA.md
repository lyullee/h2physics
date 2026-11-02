# Additively manufactured 316L hydrogen-embrittlement dataset

## Source and rights

The [official Zenodo v1 dataset record](https://zenodo.org/records/19813205) is titled *Effect of Hydrogen Embrittlement on Mechanical Properties of Additively Manufactured 316L Stainless Steel* (DOI [10.5281/zenodo.19813205](https://doi.org/10.5281/zenodo.19813205)), by Michal Kresta, Kateřina Konečná, and Petra Váňová, VSB–Technical University of Ostrava. Its record explicitly identifies the dataset license as **CC BY 4.0** and lists 23 downloadable assets (about 11.3 MB total). The machine-readable rights and file metadata, including Zenodo-listed MD5 values and direct API content URLs, are in [`research/data/am-316l-hydrogen-embrittlement.toml`](../research/data/am-316l-hydrogen-embrittlement.toml).

The record describes additively manufactured AISI 316L specimens in as-built and annealed conditions, electrolytic hydrogen charging, slow-strain-rate tensile testing, hardness measurements, and fracture/microstructure images. This provides measured material-response evidence that may complement existing hydrogen-embrittlement and vessel-integrity work. It is a single alloy/process dataset and does not establish general structural-steel behavior, gaseous hydrogen exposure equivalence, pressure-vessel qualification, fatigue-crack growth, or a fracture-toughness law.

## Intake and validation outline

All 23 files (11,274,510 bytes) were retrieved from the official Zenodo record on 2026-10-31 and stored under `research/data/payload/am-316l-hydrogen-embrittlement/`. Every downloaded file matched its publisher-listed MD5. Local SHA-256, byte count, source URL, and repository-relative payload path are recorded per file in the manifest. The dataset record names Michal Kresta, Kateřina Konečná, and Petra Váňová and states CC BY 4.0; retain this attribution and DOI citation whenever redistributing the payload. This license statement comes from the dataset record and does not apply to unrelated materials.

The raw payload is retained unchanged. Before selecting observations, audit the Excel workbook sheets and raw versus processed values. Keep charged and reference specimens, build state, heat treatment, and specimen identifiers separate; check whether charging current, time, exposed surface area, and resulting hydrogen content are fully described. Preserve raw force/displacement or stress/strain channels without unit inference. Audit the hardness sheet and image naming against the source readme, then issue a column-and-specimen mapping only where semantics are explicitly supported.

An initial workbook-structure inspection found one tensile-results sheet, six
per-specimen tensile traces, and six hardness sheets. The trace headers identify
index, position in mm, strength in MPa, and deformation; the results sheet
contains specimen identifiers, charging-rate labels, loading speed, geometry,
and tensile-property columns. Hardness sheets provide measurement date,
specimen/method, indenter readings, and hardness values. No values have been
converted or aggregated. Sheet names and channel labels alone do not prove
which tensile and hardness measurements are paired, the physical meaning of
the reported hydrogen-charge labels, or whether the deformation column is
engineering strain suitable for constitutive calibration.

Potential validation evidence is limited to descriptive comparisons of paired charged/reference specimens and reproduction of source-reported tensile/hardness summaries after units, specimen pairing, and statistical definitions are established. No direct constitutive or fracture API mapping is admitted until hydrogen concentration/charging exposure, specimen orientation, geometry, and stress/strain basis are resolved. This candidate adds no model code and makes no model-validation claim.

## Acquisition contract check

The repository's raw workbook reader was exercised locally with the acquired payload in Conda Python 3.12.14 and openpyxl 3.1.5. Both deferred entrypoints (`validate_tensile_workbook` and `validate_hardness_workbook`) returned `accepted=True`, including source hash, worksheet inventory, and lossless cell snapshot checks. This confirms the ingestion contract only: no specimen pairing, unit reinterpretation, derived property, model fit, or independent physical validation was performed. Hangang execution remains pending.