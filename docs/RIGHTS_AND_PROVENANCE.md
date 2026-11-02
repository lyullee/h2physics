# Rights and provenance

`scripts/audit_data_manifests.py --check-acquired --output
docs/DATA_MANIFEST_AUDIT.md` checks recorded acquired/historical-acquired metadata
without reading model or experimental values. `--check-metadata` instead requires
the same fields on every candidate, including intentionally withheld records.
Both modes fail on parse errors; neither grants rights or clears redistribution.
Unresolved candidate metadata and file-level review remain visible in the report.

Before publishing a GitHub source snapshot, run
`python scripts/audit_public_tree.py`. It inspects staged/index blob bytes as well
as current bytes for tracked and non-ignored untracked working-tree files, so a
staged unsafe version cannot be hidden by a safe unstaged replacement. It checks
prohibited PDF/Office documents, raw-data formats, private paths and common credential
markers. It does not follow symlinks or inspect the ignored acquisition cache. This
is a content-hygiene gate only: it does not verify copyright, source licenses,
attribution or permission to redistribute.
Run it alongside the built-archive audit after preparing the exact public tree.
Tabular/time-series and scientific binary formats, JSON/JSONL payloads, Office
documents, PDFs, native binaries and common compressed/wheel/source archives are
denied. JSON is treated as a possible raw-data container by the public-tree and
distribution audits; a reviewed metadata record that needs JSON must be converted
to an explicitly reviewed text format before inclusion. Tracked submodule
references require separate source and license review because their contents are not
ordinary files in this working tree. Temporary build/output directories are also
denied so local release artifacts cannot silently enter the source snapshot.
Any intentionally redistributed fixture needs a separate explicit license and
attribution review; do not weaken the general denylist to admit it.

Public availability and permission to redistribute are separate facts. A scientific
equation, a software implementation, a parameter table, a dataset, a figure and a
publication can each have different rights. Rewording is not a clearance method.

## Original implementation rules

- Implement equations from independently accessible primary scientific sources.
- Author comments, explanations, examples and tests from the implemented mathematics.
- Do not reproduce third-party text, figures, tables, worked examples or source code.
- Prefer maintained libraries with explicit compatible licenses instead of copying them.
- Record scientific citations and dependency licenses without implying endorsement.
- Keep private equipment inputs and nonredistributable records outside public artifacts.

## Dataset clearance

Before downloading a research dataset, preserve the repository identity, version, DOI,
authors, explicit dataset license and the metadata URL that establishes it. Record any
file-specific exceptions. Verify the publisher checksum when available, compute SHA-256,
and inspect the archive before extraction. Preserve attribution with derived results.

Priority licenses are CC0, CC BY 4.0 and clearly described public-domain dedications.
The French Open Licence 2.0 (etalab-2.0) is also admitted after reviewing the
[grantor's terms](https://github.com/etalab/licence-ouverte/blob/master/open-licence.md).
Retain the source/grantor and latest update date as well as the version/DOI.
Share-alike, noncommercial, no-derivatives, restricted or unclear records require a
separate decision. Discovery records can remain in the catalog while acquisition or
redistribution is withheld. The code license never overrides the data license.

Repository metadata constructors bind supported license identifiers to recognized
grant-text host/path pairs. Provider label matching uses exact normalized aliases,
not substring guesses; conflicting ID/URL evidence remains unresolved. Provider
metadata bytes remain unchanged and hash-bound;
when a provider supplies a supported identifier with a misleading or unrelated URL,
the public `Dataset` uses the canonical grant URL while preserving the original bytes
for audit. Receipt replay requires `rights_permitted = true` as an actual TOML boolean
and a locator consistent with its license identifier. Historical HTTP license links
may be recognized as informational provenance during replay but are never fetched;
new metadata objects require HTTPS. These consistency checks do not substitute for
file-level rights review or a grantor decision. The stdlib manifest audit reports
identifier/locator mismatches and flags historical HTTP locators.

External raw data and normalized observations are ignored by Git and excluded from
source/wheel distributions by default. Reproduction uses versioned acquisition records.
An explicitly reviewed small fixture may be added later with its license and attribution.

### Recent source records and repository redistribution scope

The BAM jet-fire record (Zenodo `10.5281/zenodo.21026781`) declares CC BY 4.0;
the hydrogen acoustic compilation (`10.5281/zenodo.21355851`), TiO2 dataset
(`10.5281/zenodo.15277951`), hydrogen-engine record
(`10.48328/tudatalib-2291`) and dark-fermentation workbook
(`10.17632/2nwcdx9hst.2`) have corresponding versioned metadata receipts and
author/DOI attribution in `research/data/*.toml`. SOE fault-operation metadata
(`10.5281/zenodo.10648884`) is a catalog-only record; no payload was acquired.
The nanoporous-carbon chemisorption files (`10.17632/vyp4wbhxzr.1`) also have a
versioned receipt, with the H2 material-basis meaning unresolved.
The license fields describe the dataset grants as stated by their repositories;
they do not license this project's code, associated papers, publisher figures,
or any embedded third-party material.

Raw-data redistribution is not admitted for these sources. Acquired payloads
remain under ignored `data/raw/`; public manifests retain metadata and
checksums, not the observations themselves. The acoustic manifest records the
omitted `pif_reader.py`; it is not copied into this repository. The BAM record
also excludes bundled thermographic assets from reuse pending separate review.
The hydrogen-engine record leaves third-party component rights unresolved. For
acoustic, TiO2, fermentation and carbon, third-party component review is explicitly
unresolved and their manifests set `raw_redistribution_admitted = false`.
SOE remains unacquired and unparsed. These records permit the documented
source-bound processing under their stated grants where applicable, but do not
clear onward redistribution of source files or model qualification.

## Release review

Inspect tracked files and the built distribution, not only .gitignore. Verify external
license/attribution records, optional mechanism provenance, source-code ownership, private
path removal and data exclusions. Retain necessary citations and notices. A clean audit
reduces identifiable risks but is not a guarantee against all legal claims.

## Optional native biological provenance

The host distributes original assembly/audit code and artifact/source/license
receipts. Actual QSDsan, BioSTEAM and Thermosteam license files were reviewed as
NCSA; their metadata naming differs in some releases and does not replace the
actual notice. The isolated native process stack is not part of the host wheel
or sdist. Keep installed notices and exact source/version evidence when building
an application that redistributes those native dependencies. The source receipt
and public primary process references do not supply missing experimental rights
or establish biological model validation.

## Native consequence and risk dependencies

Optional HyRAM6.1 is GPL-3.0-only and remains a separately installed provider;
no native implementation, probit table or original calibration dataset is in the
host archives. The host license does not relicense HyRAM or determine the license
obligations of a combined redistributed application. Preserve native notices and
review the actual application distribution before publishing that combination.

The reviewed Caltech SDToolbox distribution contains BSD-3-Clause code and the
native conditional-risk wheel is Apache-2.0 with its own LICENSE/NOTICE. Their
exact artifacts, dependency licenses and source hashes are recorded in
research/detonation_dependency.toml and research/risk_dependency.toml. Neither
native implementation is bundled. No mechanism or field observation is copied
into host source. ELVHYS BLEVE observations remain separately acquired CC0 data
with the versioned public receipt and original attribution. The native harm
calibration datasets have not been independently reviewed or redistributed.

## New optional thermal/monitoring and cold-room evidence

The host distributes original Python assembly/audits and versioned receipts.
Actual pythermalcomfortMIT, numba/llvmliteBSD notices and their original bundled
third-party notices were inspected and retained in the isolated target. The
user's native monitoring source is MIT at a pinned official revision. Neither
native source nor original coefficients, training weights or mechanism is
redistributed here. Artifact/notice hashes are in thermal_dependency.toml and
monitoring_dependency.toml; the host license does not replace native notices.

ELVHYS4.2 DOI10.18710/JXJP0H version1.1 metadata explicitly grantsCC0 and198
attachment checksums. All attachments and normalized observations remain outside
Git/distributions; public receipts preserve authors, rights, immutable file IDs,
source hashes and unresolved meanings. Dryad's official API identifies the O2-chamber
dataset as version 6 under CC0-1.0 and lists a workbook plus README with SHA-256
digests. Its attachment endpoints returned HTTP 401 to the public acquisition client
on 2026-10-30; no files or observations were acquired. The record documents in-vitro
oxygen transfer in a cell-culture chamber, so even if acquired it would inform only
general oxygen-sensor/transfer-method development and would not validate hydrogen
facility oxygen-deficiency predictions. It is not used in model calibration or
validation.
The original physiological paper citation is retained, while403 publisher access
is not represented as inspection of its full validation text or experiment.

## Coding-first optional PV/fracture ownership

The new source composes separately installed pvlibBSD and official HELPRBSD
APIs; exact reviewed source/artifact/notice records remain in their dependency
receipts. Original host geometry, scheduling and finite-inventory code does not
copy native constitutive formulas or coefficient tables. The example parameters
are explicit synthetic fixtures, not licensed experimental calibration data.
No new raw data/native implementation is added to the public artifacts.
Static license/API inspection is distinct from runtime and application review.


## Coding-only dependency review — 2026-10-28 continuation

Pool fire reuses reviewed PRCT0.1.0 Apache-2.0. Vessel failure reuses pinned
HELPR2.1.0 BSD-3-Clause, with an additional source receipt in
research/vessel_failure_dependency.toml. Parcel flight reuses installed fluids
(MIT), CoolProp (MIT) and SciPy (BSD); no new correlation coefficients or
publication prose are copied. Economics reviews optional pyH2A0.0a8: MIT code,
CC-BY4.0 non-code resources, recorded separately in
research/economics_dependency.toml. ProFAST1.0.6 was rejected on use/redistribution
terms and is not a dependency. No native installation or scientific execution
was performed for these four coding lanes. Reviewed rights are not proof of
physical validity or a legal guarantee. No third-party tables are vendored.


## Cavern/MEC/impact/front coding dependencies

Optional UH2SC is pinned to d5057350df4d86c5c11a22e76beca24275518c8c,
BSD-3-Clause with HydDown MIT origin notices; reviewed source/license hashes are
in research/underground_storage_dependency.toml. Its native/transitive Linux
installation and complete dependency-rights lock remain pending. It is not
vendored. Impact reuses existing CoolProp/SciPy/DynamicLH2PoolX, with its own
review receipt. MEC uses actual Cantera Interface plus original synthetic fixture
and shared kernels. Front propagation reuses installed Cantera/SciPy and the
shared chemistry adapter; no chemistry mechanism or graph solver is copied.
No native dependency installation or scientific execution occurred in this wave.

The DOI10.34810/data2866 MEC dataset has been acquired from its public Dataverse
bulk endpoint under the record-level CC0 grant; the OAI response and bulk archive
are hash-pinned, all 23 data-file checksums match the publisher manifest, and ten
published preview MD5 values match. The publisher exposes no file-level rights
override fields, so raw files remain ignored and outside public distributions
pending confirmation that no file-specific exception applies. Its observations
do not qualify whole-cell MEC performance. See
`research/microbial_electrolysis_data_candidate.toml` for exact receipt and schema.


## Obstacle/fire/cost/evidence coding rights

The optional external FDS6.11.1 source notice is recorded in
research/obstacle_dispersion_dependency.toml at revision
ff928dbf68a2623ced3a007be75391c6dc6c9f90. Its NIST/US-government-work notice is
preserved without a universal MIT/GPL relabel. No binary/source/thermo table is
bundled; actual binary and MPI/OpenMP/runtime/transitive review remain pending.
Jet diagnostics reuse the separate reviewed HyRAM GPL-3.0-only and Cantera BSD
owners, including installed native NASA thermochemistry rather than copied
coefficients. Their source/license byte receipts are recorded separately.
MEC economics reuses the reviewed pyH2A owner; no financial tables/formulas are
vendored. The read-only collector uses standard-library code and existing
metadata types. No new dataset assets, native installation, simulation or
scientific qualification is claimed for this checkpoint.

New mixed-origin observation source: Zenodo DOI10.5281/zenodo.13981041, CC-BY-4.0; creator attribution/checksums are in research/data/microbial-nutrient-recovery.toml and docs/MICROBIAL_OBSERVATIONS.md. Raw workbook remains ignored. Computed Minteq output is not independent measured evidence. No absolute legal clearance is asserted.

## Optional HyRAM ignition dependency

The ignition-probability adapter calls the separately installed GPL-3.0-only
`hyram.qra.ignition_probs` implementation and records the package version and
kernel source hash. It does not copy the native probability table or vendor
HyRAM code/data. Downstream redistribution that combines this optional
dependency remains subject to the dependency's GPL terms. This dependency
review is not a legal conclusion for combined distributions; see
`docs/HYRAM_IGNITION_PROBABILITY.md`.
