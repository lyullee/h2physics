# Publication status: 0.1.0

Project/distribution/import: **h2physics**. Original work: Apache-2.0. Research maturity: Alpha.

| Destination | Verified outcome |
| --- | --- |
| GitHub | [Public repository](https://github.com/lyullee/h2physics) and [0.1.0 Alpha release](https://github.com/lyullee/h2physics/releases/tag/v0.1.0) published on 2026-11-02. |
| PyPI | No upload performed. Trusted Publisher setup and actual registry publication remain pending. A name lookup is not a reservation. |
| Zenodo | No deposit submitted or DOI verified in this task. GitHub integration or a manual software deposit remains pending. |

The release is public and marked prerelease/Alpha; it is not a draft. Reviewed source commit: `762bfa0348fe2207783924b9e1fc5750b89bc940`. The two attached distributions and SHA256SUMS.txt were confirmed as uploaded. GitHub-reported digests match the local SHA-256 values. The Linux build/audit workflow at the release tag also passed; its publishing job was explicitly skipped. See [release evidence](RELEASE_EVIDENCE_0_1_0.md).

## Reproduction and continuation

Read [Publishing](PUBLISHING.md), [Publication audit](PUBLICATION_AUDIT.md), [Development history](DEVELOPMENT_HISTORY.md), and [Research continuation](RESEARCH_CONTINUATION.md). Build/check receipts are separate from experimental model qualification.

The public source starts with fresh Git history. Original code, original explanations, tests, manuals, scientific attribution and reviewed source metadata are retained. External observations, third-party payload images, private configuration and installed engine source are acquired separately. Existing local development history was preserved separately.

## Remaining service work

Configure a PyPI Trusted Publisher for owner lyullee, repository h2physics, workflow release.yml, environment pypi. Run the workflow at v0.1.0 with publish_pypi=true only after that setup; verify the actual registry version and installation. The default workflow only builds and cannot publish by default.

Enable Zenodo integration before a future release intended for automatic archival, or manually deposit the reviewed 0.1.0 software assets. The existing GitHub release alone is not a verified Zenodo deposit. Add a DOI to CITATION.cff only after the service assigns it. Keep the dataset/engine exclusions in the deposited software.

Documentation and post-build receipts can advance on main after the frozen release tag. They do not change the already uploaded assets or imply that differently rebuilt archive hashes must match timestamped local builds.
