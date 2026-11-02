# Publication status

## 0.2.0 Alpha update — preparation on 2026-11-03

The new version packages the tested model-level extensions. PyPI and Zenodo
publication are **pending service verification** at this preparation checkpoint.
A GitHub push, workflow dispatch, draft record or reserved DOI is not recorded
as a completed publication. Read [0.2.0 release evidence](RELEASE_EVIDENCE_0_2_0.md)
for the source/change boundary and required archive/install checks.

| Destination | Verified state at preparation |
| --- | --- |
| GitHub | [Eight model-level extensions](ENHANCEMENTS_20261102.md) are on main at `13a4f6068c560a7425ffdf500d86a8eedec6986a`; the two-job [model CI](https://github.com/lyullee/h2physics/actions/runs/41471065252) passed. The final 0.2.0 metadata-updated source/tag is not yet recorded here. |
| PyPI | Version 0.2.0 publication is not yet verified. The last confirmed public registry version is 0.1.0 below. |
| Zenodo | A new 0.2.0 public version and version DOI are not yet verified. The existing 0.1.0 record and all-version concept DOI below remain intact. |

After publication, record the actual source revision, service URLs, file hashes,
new version DOI and registry installation result. Keep the earlier release
identities below unchanged. The publication update does not increase physical
qualification or turn the 61 broader environment blockers into passes.

## Historical verified release: 0.1.0

Project/distribution/import: **h2physics**. Original work: Apache-2.0. Research maturity: Alpha. **The three 0.1.0 publication destinations were verified complete.**

| Destination | Verified public outcome |
| --- | --- |
| GitHub | [Repository](https://github.com/lyullee/h2physics) and [0.1.0 Alpha release](https://github.com/lyullee/h2physics/releases/tag/v0.1.0), published 2026-11-02. |
| PyPI | [h2physics 0.1.0](https://pypi.org/project/h2physics/0.1.0/), published 2026-11-02 through the scoped GitHub Trusted Publisher. Both registry files were downloaded and verified; isolated registry installation and documented smoke calculations passed. |
| Zenodo | [Public software record 23886390](https://zenodo.org/records/23886390), version DOI [10.5281/zenodo.23886390](https://doi.org/10.5281/zenodo.23886390); concept DOI [10.5281/zenodo.23886389](https://doi.org/10.5281/zenodo.23886389). Source distribution, wheel and checksum list deposited. |

Reviewed source tag: [v0.1.0](https://github.com/lyullee/h2physics/tree/v0.1.0), commit `762bfa0348fe2207783924b9e1fc5750b89bc940`. GitHub is a public prerelease/Alpha, not a draft. The DOI was added to current CITATION.cff only after actual Zenodo publication. Detailed hashes, times and check scope: [registry/archive receipt](REGISTRY_ARCHIVE_RECEIPT_0_1_0.md) and [original release evidence](RELEASE_EVIDENCE_0_1_0.md).

### Historical 0.1.0 installation

```bash
python -m pip install "h2physics[thermo,hydraulics]==0.1.0"
```

Python 3.12 is the recorded reference interpreter. Additional specialist engines and their licenses/qualified revisions remain separate; the standard install does not install every optional native engine.

### Continuing the work

Read [Publishing](PUBLISHING.md), [Publication audit](PUBLICATION_AUDIT.md), [Development history](DEVELOPMENT_HISTORY.md), and [Research continuation](RESEARCH_CONTINUATION.md). Distribution checks do not expand the experimental qualification of any model.

The public Git history starts from an audited source snapshot. Original local history was preserved separately. External raw observations, source reference documents, third-party payload images, installed engines, credentials and local artifacts are excluded. Scientific attribution and reviewed acquisition metadata remain public.

The scoped PyPI publisher is configured for owner lyullee, repository h2physics, workflow release.yml, environment pypi. The default workflow only builds. A future publication requires a reviewed new version/tag and explicit publishing dispatch; do not overwrite or retarget v0.1.0. Zenodo 0.1.0 was a manual deposit; automatic GitHub-Zenodo integration was not enabled by this task.

Post-publication documentation on main can contain the final service receipts and DOI without altering the immutable initial tag or uploaded archives. Windows local release assets and Linux CI registry assets have different packaging hashes; see the receipt for their distinct identities.

## Relationship to the development checkpoint

The [eight model-level extensions](ENHANCEMENTS_20261102.md) were implemented and
checked as 0.2.0.dev0. Their scientific/software evidence remains that recorded
checkpoint. The 0.2.0 publication preparation changes release metadata and
documentation, not physical equations or defaults. New service records must
identify the later frozen release source without relabeling the earlier test
artifacts or modifying the 0.1.0 publications.
