# Publication content and provenance audit — 2026-11-02

This report records release-preparation checks for the original h2physics host
source and documentation. It is a technical content/provenance review, not a
legal opinion, a guarantee of non-infringement, or scientific qualification.
The final public snapshot and its actual wheel/source archives must pass their
own final content checks after all release edits finish.

## Checks actually executed

| Check | Observed result | Scope limit |
| --- | --- | --- |
| Initial Git-bound tree/index scan | 1,556 files inspected; script returned PASS | The initial scanner did not cover external image payloads or all account identifiers. Its PASS alone was insufficient. |
| External payload inventory | Found an untracked external measurement payload directory containing 20 images and associated metadata | These files are not original code or documentation and were excluded rather than relabeled as project assets. |
| Private execution-identity search | Found personal local/cluster defaults in four staging tools and historical documentation | Public GitHub author/source URLs are legitimate attribution and were retained. |
| Protected-source phrase screening | Three local reference documents, 1,450 pages, screened against 2,790 text files visible during preparation | The text inventory temporarily included an unpacked build tree; final publication excludes that duplicate tree. |
| Phrase review | Zero substantive contiguous matches of at least 12 normalized English words; the only candidate was repeated scientific-notation letters | Screening is not exhaustive proof about shorter wording, paraphrases, images, equations, source code or rights. |
| Four optional staging scripts | AST parse and targeted Ruff checks passed after parameterization | No remote operation, authentication or computational job was executed. |

The phrase-screen source names, page snippets and intermediate extraction are
kept in an ignored local audit artifact. No protected passages, reference images
or complete source texts are reproduced in this public report. There is no claim
that automatic rewriting by itself clears reuse rights.

## Public-file exclusions

The release preparation excludes external acquisitions under data/raw and
research/data/payload, generated outputs under artifacts, private execution
receipts, work environments and extracted build trees. Original reference files,
workbooks, native binaries, external package archives and individual measured
rows are not release assets. The payload exclusion was added to Git selection
and source-distribution rules; publication scanners also reject that directory.
Do not weaken these exclusions merely to make an example or native test run.

The parent release task checks the actual source distribution and wheel after
building. A Git ignore rule alone is not evidence that an already-indexed file
or a built archive is safe. The existing source history is kept locally; the
public release uses a fresh, sanitized snapshot rather than blindly exporting
all historical Git objects. The working-tree audit does not scan historical
commits for every credential or deleted asset.

## Execution configuration changes

Four optional shared-session tools now require explicit local task configuration:

- H2PHYSICS_WSL_USER: the user of an already-open WSL session.
- H2PHYSICS_RUN_WRAPPER: an absolute normalized path whose final component is run.sh.
- H2PHYSICS_REMOTE_ROOT: an explicit normalized workspace beneath /scratch/.
- H2PHYSICS_WSL_DISTRIBUTION: optional distribution identifier; default Ubuntu-22.04.

Personal defaults were removed. Each invocation still uses the existing
wsl.exe /bin/bash run.sh mechanism. Missing configuration, traversal, malformed
paths and a different wrapper filename are refused. No new SSH connection,
password prompt or OTP workflow was introduced. Syntax/lint checks are the
only checks performed on these remote utilities during publication preparation.
See [Hangang execution configuration](HANGANG_EXECUTION.md).

## Licenses and attribution

The original host code/documentation has an Apache-2.0 license and project
NOTICE. The [authoritative Apache license](https://www.apache.org/licenses/LICENSE-2.0)
requires applicable license/attribution notices to be retained on redistribution.
The project notice does not relicense external datasets, mechanisms, native
solvers, their documentation or embedded third-party material.

Dependencies are separately installed, and the package design does not vendor
native solver implementations. In particular, the optional HyRAM+ dependency
retains its GPL-3.0-only terms; it is not presented as Apache-licensed project
code. A combined redistribution needs its own compatibility and notice review.
See [Third-party inventory](THIRD_PARTY.md),
[dependency decisions](DEPENDENCIES.md) and
[rights/provenance rules](RIGHTS_AND_PROVENANCE.md).

Scientific citations and dataset author/DOI/version/license/checksum records are
retained. Removing an original passage does not justify removing legitimate
scientific attribution. Acquisition and a dataset-level grant do not establish
that every embedded component is cleared for onward redistribution. Unreviewed
raw files remain outside public assets. This audit does not certify all
upstream licenses, code-clone absence or patent clearance.

## Final release gates

Before marking a release public, run the exact-snapshot Git-bound content audit,
build both distributions, run the actual archive audit and install the resulting
wheel in a clean environment. Check the basic documented imports/examples, not
only editable development installation. Preserve the release version, content
hashes, dependency set, test receipts and remaining scientific limitations.
GitHub/PyPI/Zenodo publication outcomes must be recorded only after their
respective services confirm the actual uploaded record.
