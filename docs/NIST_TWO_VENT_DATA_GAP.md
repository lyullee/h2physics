# NIST two-vent enclosure data: reuse clearance gap

Status: source files are publicly linked, but this repository has not established an eligible dataset license. Do not download into the project, redistribute, or create a dataset reader/observation case until the rights record is resolved.

## Candidate and relevance

NIST TN 1694 describes 18 quarter-scale two-car-garage tests in a 1.5 m × 1.5 m × 0.75 m enclosure. The test program varied vent count/size/location and release location, and reports time histories at vertical measurement positions plus differential pressure. Helium was used as a hydrogen surrogate. These records are relevant to checking qualitative stratification, vent exchange and concentration-history behavior of `TwoVentHydrogenLayer`, but they are not direct hydrogen measurements and require explicit surrogate/scale limitations in any future comparison.

The NIST Fire Research Division page identifies the actual payload as 18 Excel workbooks in a 53 MB ZIP and links the archive from Appendix A. Archive endpoint: <http://www.nist.gov/el/fire_protection/buildings/upload/HeliumDispersionDataSets.zip>. This is evidence that the data files are available from the primary agency page; no payload has been acquired or inspected here.

## Rights finding

The TN 1694 publication record and its linked Appendix A data archive do not state CC0, CC BY, or another dataset-specific license. NIST's separate general policy says NIST employee-created non-SRD works are generally uncopyrighted in the United States and describes worldwide derivative/distribution permission where NIST may hold foreign rights. That policy also notes that NIST can hold rights assigned by contractors. It is not an explicit CC0/CC-BY declaration attached to this archive, and the archive record does not identify creator/rights metadata at file level. The repository's data policy admits explicitly stated CC0/CC-BY/public-domain grants; therefore this candidate does not currently pass acquisition or redistribution clearance.

This is a permission-record gap, not a claim that the dataset is necessarily restricted. The journal article's license or accessibility is not a substitute for a dataset grant.

## Exact clearance request

Request from the NIST Fire Research Division contact listed on the data page (William Pitts, william.pitts@nist.gov), or the NIST publication contact:

1. Confirm that the linked `HeliumDispersionDataSets.zip` and all 18 spreadsheets are NIST employee-created data with rights available for worldwide copying, modification, and redistribution, including in a public GitHub repository; identify any contractor or other third-party contributions and exclusions.
2. Provide a dataset-level rights statement or repository record explicitly licensing the archive under CC0 1.0 or CC BY 4.0 (preferred), or an equivalent written grant that satisfies this repository's published data-clearance policy.
3. Confirm whether the linked archive is the current complete version and provide a stable HTTPS URL, archive version/date, and checksum if maintained.
4. Provide the test-to-workbook mapping and measurement-column/unit/key definitions needed to interpret concentration and differential-pressure traces without relying on inferred labels.

Once resolved, acquire only the few experiments that exercise the two-vent buoyant-layer envelope, preserve original files outside the public source tree, bind source version/file hashes and case identifiers in a manifest, and implement a source-bound reader plus a deferred Hangang ingestion/observation case. Do not duplicate the separate open hydrogen-channel dataset (`research/data/hydrogen-channel.toml`), which has a different geometry and data provenance.

## Evidence

- NIST TN 1694 record (experiment design, helium surrogate, conditions, Appendix A pointer): <https://www.nist.gov/publications/experimental-characterization-helium-dispersion-scale-two-car-residential-garage-nist>
- NIST Fire Research Division dataset description and exact archive link (18 spreadsheets, 53 MB): <https://www.nist.gov/el/fire/hydrogen-flammability-detection-and-fire-safety>
- NIST general copyright/fair-use/licensing policy (not a dataset-specific CC0/CC-BY record): <https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications>
- Buoyant two-vent model publication record: <https://www.nist.gov/publications/vertical-release-hydrogen-partially-enclosed-compartment-role-wind-and-buoyancy>

Reviewed 2026-10-31. No experimental values were copied, parsed, or computed for this note.
