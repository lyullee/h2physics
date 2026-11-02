# Publishing h2physics

Version 0.2.0 is being prepared as an Alpha update to the published 0.1.0 release.
The original code/documentation uses Apache-2.0; external providers and datasets
retain their own terms. See [current publication status](PUBLICATION_STATUS.md),
[0.2.0 release evidence](RELEASE_EVIDENCE_0_2_0.md),
[publication audit](PUBLICATION_AUDIT.md), [rights/provenance](RIGHTS_AND_PROVENANCE.md)
and [the historical 0.1.0 service receipt](REGISTRY_ARCHIVE_RECEIPT_0_1_0.md).

## Current 0.2.0 update

The release packages the tested eight-work-package checkpoint at source commit
`13a4f6068c560a7425ffdf500d86a8eedec6986a`. Release metadata, version and publication
documentation change; equations, provider choices and physical defaults do not.
The final release tag must identify the reviewed metadata-updated source, rather
than the earlier development commit. Its exact identity belongs in the confirmed
service receipt after freezing.

Use the existing PyPI Trusted Publisher and Zenodo record's New version flow.
Keep version 0.1.0, its DOI and its file objects intact. For the new deposit,
prefer the exact publicly downloaded and hash-verified 0.2.0 registry files plus
a checksum list, so any cross-service equality claim can be verified directly.
If separate builds are used, retain their distinct hashes instead of implying
that equal version labels make their archive bytes identical. Creating a draft,
reserving a DOI or dispatching a workflow is not completed publication.

## Prepare a new reviewed version

Keep external data, reference documents, images, installed engines, local environments, credentials and execution caches outside Git and distributions. Preserve the source and rights metadata needed to acquire external inputs separately. The first public release used a fresh sanitized Git history while retaining local history privately; continue normal reviewed development from the public repository rather than replacing it with unreviewed history.

Update package version, changelog, current user/API manuals and release scope. Use absolute README links that work in registry rendering. Build wheel and source distribution, run strict Twine checks, inspect their actual members with scripts/release_audit.py, audit staged/current Git content with scripts/audit_public_tree.py, and exercise the installed wheel outside the checkout. Keep numerical verification separate from measured validation and application qualification. A documentation correction is not new model evidence.

Review and tag the exact source before publication. Do not rewrite an existing tag or try to replace an already uploaded version. Store hashes and source revision in release notes. Post-build receipts can follow the tag on main without pretending they were embedded in the earlier archives.

## GitHub

Repository: https://github.com/lyullee/h2physics . Attach the checked distribution files and checksum list to the matching public research release. Keep Alpha/prerelease status explicit. Record service-confirmed upload outcomes and digests. GitHub source archives, manually built assets and registry CI assets are distinct archive objects even when package Python source is equivalent.

## PyPI

Distribution/import: h2physics. The active Trusted Publisher binds owner lyullee, repository h2physics, workflow release.yml and environment pypi. This was registered with explicit owner approval. No persistent upload token is stored in source. The manual workflow default only builds; publishing is enabled only by an explicit publish_pypi=true dispatch at the reviewed version tag.

For 0.1.0, the publishing workflow succeeded at v0.1.0: https://github.com/lyullee/h2physics/actions/runs/41454375606 . Verify the public registry version, both file digests and installed package after each publication. Compare actual registry package source against the reviewed Git revision, not just an editable workstation import. PyPI files for an existing version are immutable release artifacts; metadata/README corrections belong in a subsequent version.

## Zenodo

The 0.1.0 manual software deposit is https://zenodo.org/records/23886390 . Version DOI: 10.5281/zenodo.23886390. All-version concept DOI: 10.5281/zenodo.23886389. It archives the reviewed GitHub local-build source distribution, wheel and SHA256SUMS.txt, not the separately built PyPI file objects.

Use the existing record's New version flow for a later version in the same concept series. Supply the actual version, author, software type, first-publication date, Apache-2.0 license, original description, source URL, reviewed files and checksums. Do not invent a DOI or affiliation. Verify public status and file hashes after publication, then update CITATION.cff and current service records. Automatic GitHub-Zenodo integration was not configured; do not assume a later GitHub release will be archived automatically.

## Record the outcome

Publish actual URLs, DOI, source revision, archive hashes, dependency set, install results and remaining scientific limitations. Keep private authentication and local tool/session details only in ignored local handoff files. Do not claim all services are complete from a workflow dispatch, draft DOI reservation or GitHub push alone.
