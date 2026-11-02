# h2physics 0.1.0: registry and archival receipt

This records actual service publication and distribution checks on 2026-11-02. It adds no model equations and does not expand physical qualification. The earlier [release evidence](RELEASE_EVIDENCE_0_1_0.md) records the reviewed Windows build and clean local-wheel installation.

## Published identities

| Service | Actual public record |
| --- | --- |
| GitHub | [Repository](https://github.com/lyullee/h2physics), [Alpha release v0.1.0](https://github.com/lyullee/h2physics/releases/tag/v0.1.0) |
| PyPI | [h2physics 0.1.0](https://pypi.org/project/h2physics/0.1.0/), files uploaded 2026-11-02T13:36:47Z and 13:36:49Z |
| Zenodo | [Record 23886390](https://zenodo.org/records/23886390), public software, created 2026-11-02T13:41:30Z |

Version DOI: [10.5281/zenodo.23886390](https://doi.org/10.5281/zenodo.23886390). All-version concept DOI: [10.5281/zenodo.23886389](https://doi.org/10.5281/zenodo.23886389). Zenodo reports version 0.1.0, publication date 2026-11-02, author Lee, Ugwiyeon, open access and Apache License 2.0. Current CITATION.cff was updated after publication, not from an invented or unregistered DOI.

All distributions use the reviewed source revision `762bfa0348fe2207783924b9e1fc5750b89bc940` / tag v0.1.0. Post-publication manuals, DOI and receipts follow that immutable tag on main.

## PyPI publishing path and files

The owner explicitly approved a Trusted Publisher limited to GitHub owner lyullee, repository h2physics, workflow release.yml and environment pypi. No persistent upload API token was created or stored in source. The publish-enabled run [41454375606](https://github.com/lyullee/h2physics/actions/runs/41454375606) succeeded at the reviewed tag; its publishing job finished 2026-11-02T13:36:54Z. The earlier build-only run remains separate evidence.

| Registry file | Bytes | SHA-256 | Package Python files | Frozen Git-source match |
| --- | ---: | --- | ---: | --- |
| h2physics-0.1.0-py3-none-any.whl | 1631557 | `3c99830bd55e6706c1852b72c7b93c238b609aaf92e6e20fd60458f30ed01fec` | 365 | PASS |
| h2physics-0.1.0.tar.gz | 5013302 | `225a89aac4583a0c711bcf8a6c71ab7bda642151a24acd25b4be4ef2b884bf50` | 365 | PASS |

Both files were fetched from the version-specific public PyPI metadata and files.pythonhosted.org URLs. SHA-256 matched the registry digests. Every one of the 365 package Python files matched the frozen public Git revision byte-for-byte; no missing, unexpected or different source files were accepted.

## Actual registry installation

The previously created isolated Python 3.12.16 environment was force-reinstalled from the public index with cache disabled and without using an editable checkout:

```bash
python -I -m pip install --index-url https://pypi.org/simple --no-cache-dir --force-reinstall --no-deps h2physics==0.1.0
python -I -m pip check
```

Its previously installed NumPy 2.5.4, SciPy 1.18.1, CoolProp 8.0.0 and fluids 1.3.1 were retained. pip check found no broken requirements. The smoke ran from a separate empty working directory with Python -I and asserted imports came from site-packages. It checked version/import, native CoolProp state, steady pipe calculation and the demonstration electrochemical stack.

- Hydrogen density at 200,000 Pa and 300 K: 0.16144746212591646 kg/m³.
- Converged reference pipe mass flow: 0.00021427484849277764 kg/s.
- Stack H₂ production: 0.0005182134828131087 mol/s.
- Stack electric input: 142.81659542670673 W.

This verifies public installation and these documented examples, not independent native-engine physics or 78 full physical operating envelopes.

## Zenodo software deposit

The deposit was published manually using the logged-in account. It contains the exact reviewed local-build GitHub assets and checksum list:

| Public download | Bytes | SHA-256 | Exact reviewed-asset match |
| --- | ---: | --- | --- |
| SHA256SUMS.txt | 190 | `9fda8b7045153fb676ba329b08d8a56a74255620bd5ebd18d008f56afbf003a5` | PASS |
| h2physics-0.1.0.tar.gz | 5047511 | `e274226e3ad3685d60dfe8b5337c4be77db3aac597f75bde8175059038e84f9e` | PASS |
| h2physics-0.1.0-py3-none-any.whl | 1632165 | `0fccc59658f9cedd5479ef175069f1d41443e7ab05e252b71db572dc18cbd4b6` | PASS |

All three Zenodo files were downloaded from the public record without account credentials. Their payloads matched the reviewed local originals byte-for-byte; reported MD5 values also matched. Public record status was published, not a draft or a reserved DOI alone. Manual archive publication does not establish automatic GitHub integration; no such integration was enabled.

## Distinct archive objects and documentation limits

PyPI packages were built on Linux by GitHub Actions at the reviewed tag. GitHub attached assets and the Zenodo deposit preserve the reviewed Windows local build. Their ZIP/tar metadata, build times and Git-normalized versus working-tree line endings can differ, so whole-archive hashes and byte counts are deliberately recorded separately. No equality between these distinct archive files is claimed. Their package sources were checked against the appropriate frozen working/public Git sources.

The initial 0.1.0 archives and PyPI long description retain the README as it existed at build time, including publication-preparation wording and relative documentation links. Those historical file objects are not replaced after publication. Use the project Repository/Documentation links to current GitHub manuals and this receipt for actual publication status. Main README links have been made absolute for future registry rendering; a later distribution version is needed to update the immutable PyPI description.

External raw/processed observations, reference documents, third-party payload images, installed engine source, native binaries, credentials and local execution artifacts remain excluded. Scientific references and reviewed acquisition metadata remain available. Public release and a DOI do not certify copyright clearance, full physical validation or a whole-facility application. See [publication audit](PUBLICATION_AUDIT.md) and [research continuation](RESEARCH_CONTINUATION.md).
