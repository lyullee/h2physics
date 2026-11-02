# Publishing h2physics

Version0.1.0 is the first public research candidate. Apache-2.0 covers original host code and documentation; optional providers and datasets retain their own terms. See PUBLICATION_AUDIT.md and RIGHTS_AND_PROVENANCE.md.

## Release content

Build a clean source snapshot from the audited source allowlist, retaining local/private development history separately. Do not upload data/raw, artifacts, research/data/payload, external engines, source reference documents, credentials or local runtime configuration. Audit the Git index as well as current bytes. Build wheel and sdist and inspect their actual members. Check installation outside the checkout.

## GitHub

Target repository: https://github.com/lyullee/h2physics . Use a fresh sanitized initial source commit rather than exposing unreviewed local history. A release should attach the checked wheel and sdist. Record exact hashes and source revision in the release notes. Do not describe the conditional physical comparisons as general experimental qualification.

## PyPI

Distribution/import name: h2physics. Candidate version:0.1.0. The release workflow is .github/workflows/release.yml; its default only builds. Publishing requires a configured PyPI Trusted Publisher for owner lyullee, repository h2physics, workflow release.yml, environment pypi. The initial pending-publisher setup is at https://pypi.org/manage/account/publishing/ . A logged-in browser alone is not a package-upload credential. Never put a persistent upload token into source.

After configuration, manually dispatch the workflow at the reviewed v0.1.0 tag with publish_pypi=true. A newer documentation-only main commit is not a replacement for the release tag. Verify the actual PyPI project/version and install that version from the registry before marking publication complete. Name availability is not guaranteed by an HTTP404 alone.

## Zenodo

Use CITATION.cff for software title, author, version and Apache-2.0 metadata. Enable the GitHub repository in the existing Zenodo account before publishing a new GitHub release, or manually upload the checked software source archive. Existing GitHub releases may require manual archival. Reserve a DOI only through an actual draft; do not invent a DOI or badge. Confirm release metadata and verify the final public record. Do not upload raw experiments, installed dependencies or the original reference corpus.

## Operational status

Actual URLs, DOI and registry status must be recorded only after server confirmation. Browser session availability and any pending authentication/authorization steps belong in the local handoff, not credentials in the public repository.
