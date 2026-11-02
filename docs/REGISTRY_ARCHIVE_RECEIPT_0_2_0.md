# h2physics 0.2.0: registry and archival receipt

This records the 0.2.0 Alpha publication update on 2026-11-03 in Asia/Seoul.
Service timestamps below are UTC; a 2026-11-02 UTC upload can therefore belong
to the following Korean calendar date. The update packages existing verified
implementation and adds no physical equation or new application qualification.

## Frozen source and service state

The reviewed source is tag
[`v0.2.0`](https://github.com/lyullee/h2physics/tree/v0.2.0), commit
`efb8f17be9a353e790ea7b2f76a17db7009bcea8`. The earlier implementation checkpoint
is `13a4f6068c560a7425ffdf500d86a8eedec6986a`; release metadata, citation text and
README links changed without changing its equations or physical defaults.

| Service | Confirmed state |
| --- | --- |
| GitHub | [Public Alpha/prerelease v0.2.0](https://github.com/lyullee/h2physics/releases/tag/v0.2.0) at the frozen source above, with three attached payloads downloaded and byte-verified. Both jobs in [model CI 41473688845](https://github.com/lyullee/h2physics/actions/runs/41473688845) succeeded. |
| PyPI | [h2physics 0.2.0](https://pypi.org/project/h2physics/0.2.0/) published through the existing scoped Trusted Publisher; both public files downloaded and verified. |
| Zenodo | [Public record 23889027](https://zenodo.org/records/23889027), version DOI [10.5281/zenodo.23889027](https://doi.org/10.5281/zenodo.23889027), version 0.2.0. Three public downloads match the reviewed registry files/checksum manifest byte-for-byte. |

The historical 0.1.0 tag, PyPI files and version DOI
[10.5281/zenodo.23886390](https://doi.org/10.5281/zenodo.23886390) remain intact.
The concept DOI
[10.5281/zenodo.23886389](https://doi.org/10.5281/zenodo.23886389) continues to
identify the version series. The new version DOI was recorded only after actual
publication and public-download verification.

## Actual PyPI publishing path and files

The publish-enabled GitHub workflow
[41473689248](https://github.com/lyullee/h2physics/actions/runs/41473689248)
succeeded at the reviewed tag. It reused the existing owner/repository/workflow/
environment binding: lyullee, h2physics, release.yml, pypi. No new persistent
upload token or broader publisher permission was required.

| Registry file | Uploaded UTC | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| h2physics-0.2.0-py3-none-any.whl | 2026-11-02T15:40:02.592418Z | 1669439 | `c1a9eab69156a4b45ec0379318184047cf275fadf12258b976a843692faf2df2` |
| h2physics-0.2.0.tar.gz | 2026-11-02T15:40:04.728013Z | 5103895 | `7ae907cd2ca2b5ef39b7dc70469aeaa0e1d1645f32478a89508ee9ba8d3dda50` |

Public registry metadata and payload verification completed at
2026-11-02T15:43:58.004219+00:00. Downloaded payload sizes/digests match the
version-specific registry metadata. Every one of the **375 package Python
files in each archive** matches the frozen Git source byte-for-byte, with no
missing, unexpected or changed package Python member.

The generated `SHA256SUMS.txt` lists these two verified file digests. It is
188 bytes, SHA-256
`0a67d6e727bae7663674953b1ca76b529701a82150704d46ab7d3b651e50a18d`.
It is an archive manifest generated from verified payloads, not a third PyPI
distribution file.

## Distinct archive objects and comparison bases

The reviewed local Windows build and the registry Linux CI build have different
whole-archive objects. Their file names/version alone do not establish byte
identity:

| Local prepublication build | Bytes | SHA-256 |
| --- | ---: | --- |
| h2physics-0.2.0-py3-none-any.whl | 1670045 | `553d81d09465c045767e364e91dd423de24904814670d48828c41fca21f52522` |
| h2physics-0.2.0.tar.gz | 5137412 | `f3dccefffc6149e562f79771d0c880752b20967d22c72b925c5bd7c8105822aa` |

The local archive audit passed against the reviewed Windows working source:
375 package Python files in each archive, zero missing/unexpected/different
members. Strict Twine metadata checks also passed.

An initial registry-archive comparison against that Windows working tree
reported **25 byte differences** in each archive. All 25 were confirmed to be
CRLF-versus-LF only. This result remains an explicit comparison-basis finding;
it is not relabeled as a byte match. The registry's exact match is instead
against the frozen, Git-normalized tag source. Archive timestamps, metadata and
compression also affect whole-file digests. The content audit was rerun against an exact frozen-tag source tree and
passed for both registry archives: 375 package Python members, zero missing,
unexpected or different bytes. Archive exclusions, unsafe-path/credential
markers and license/continuation checks passed on that basis. The earlier
working-tree comparison remains retained as a failed comparison against a
different byte representation.

## Executed local 0.2.0 installation check

The local 0.2.0 wheel was installed outside the source checkout. Its isolated
smoke ran with Python `-I`, verified the version and `site-packages` import
location, and completed `pip check` without broken requirements. Observed
representative outputs were:

| Check | Actual result |
| --- | --- |
| CoolProp H2 density at 200,000 Pa and 300 K | 0.16144746212591646 kg/m³ |
| Finite-stock mechanical expansion reference | 3849478.3991721305 J |
| SDOF energy-balance residual | 1.612668332207079e-13 J |
| Synthetic Tafel slope | 0.1199999999999999 V/decade |
| Native thermal-cycle net shaft power | 35392.49266789714 W |
| Native cycle physical-exergy balance residual | −7.275957614183426e-12 W |

The actual public registry version was then force-installed from the public
PyPI index without cache, outside the checkout. `pip check` found no broken
requirements and the separate smoke ran with Python `-I`.
Its import and distribution metadata both reported 0.2.0 from `site-packages`,
and the same six representative checks completed with the values above.
The registry installation was separately replayed through the focused suite:

| Actual registry installation profile | Recorded outcome | Counting |
| --- | --- | --- |
| Main scientific profile | 137 passed, 2 skipped in 39.51 s | Two genuine-native indoor cases require the separate HyRAM runtime |
| Genuine HyRAM profile | 9 passed in 4.90 s | Completes the two omitted cases; seven repeated input cases are not added again |
| Combined selected scope | 139 distinct completed cases | 92 new checks and 47 related existing checks |

These are actual package installation and selected numerical/native-interface
checks. They do not independently validate native engine internals, real device
accuracy or a full physical catalogue. The broader environment blockers below
remain unchanged.

## Existing implementation evidence retained

The [extension checkpoint](ENHANCEMENTS_20261102.md) records 92 new and 47 related
existing checks: 139 distinct cases across main and genuine-native profiles.
The installed development-wheel main profile passed 137 and skipped two native
indoor cases; its isolated HyRAM profile passed nine, filling both missing cases
without counting seven repeated input cases again. Eight executable Python
blocks across six manuals completed. The broader 414-case control remains
348 passed, 61 environment/local-artifact failures and five skipped, unchanged
from its baseline. These facts are not expanded by the new version label.

## Zenodo archival completion

The new version was published in the existing concept series as
[record 23889027](https://zenodo.org/records/23889027), version DOI
[10.5281/zenodo.23889027](https://doi.org/10.5281/zenodo.23889027). The service
reports version 0.2.0, publication date 2026-11-03, published/open status and
Apache License 2.0. Its legacy API license identifier is `apache2.0`; this is
not a change to the package's Apache-2.0 license expression. The record reports
creation at 2026-11-02T15:48:58.461914+00:00; public-record/file verification
completed at 2026-11-02T15:50:37.431150+00:00. These are distinct service fields,
not an invented exact publication instant.

All public Zenodo payloads were downloaded without account credentials and
compared with the verified registry wheel/source files and generated manifest.
SHA-256, byte counts and the record's reported MD5 values matched:

| Zenodo and attached GitHub release payload | Bytes | SHA-256 | Zenodo MD5 |
| --- | ---: | --- | --- |
| h2physics-0.2.0-py3-none-any.whl | 1669439 | `c1a9eab69156a4b45ec0379318184047cf275fadf12258b976a843692faf2df2` | `6dc152d9bebfd47e171632ba28a2516e` |
| h2physics-0.2.0.tar.gz | 5103895 | `7ae907cd2ca2b5ef39b7dc70469aeaa0e1d1645f32478a89508ee9ba8d3dda50` | `adcc5ffd271365728b8ea8a1d17a799c` |
| SHA256SUMS.txt | 188 | `0a67d6e727bae7663674953b1ca76b529701a82150704d46ab7d3b651e50a18d` | `f0c8958b09ad7aadbf241432a57d342d` |

The same three attached assets were downloaded from the public GitHub release
and compared byte-for-byte with these registry/manifest originals. Thus the
0.2.0 attached GitHub assets and Zenodo files deliberately preserve the same
objects; the first two also equal their PyPI distributions. This equality does
not include GitHub's automatically generated source archives or the separate
local Windows build. `SHA256SUMS.txt` is not a PyPI distribution upload.
Version 0.1.0 and its DOI are preserved. No automatic GitHub–Zenodo publishing
integration was enabled by this manual new-version deposit. Citation metadata
can now use the confirmed new version DOI.

Post-publication receipts follow the frozen release tag on main. They do not
retroactively enter or replace its immutable PyPI/source archive files. External
raw observations, supplied source assets, third-party images, native package
trees, credentials and local execution artifacts remain excluded. Original
scientific attribution and the providers' own licenses remain applicable.
