# h2physics 0.1.0 distribution and publication receipt

This is release engineering evidence, not a new physics-validation campaign. Scientific results and limitations are recorded in [Development history](DEVELOPMENT_HISTORY.md) and [Research continuation](RESEARCH_CONTINUATION.md).

## Frozen source and public outcome

- Source tag: [v0.1.0](https://github.com/lyullee/h2physics/tree/v0.1.0).
- Source commit: `762bfa0348fe2207783924b9e1fc5750b89bc940`.
- Public release: [h2physics 0.1.0 Alpha](https://github.com/lyullee/h2physics/releases/tag/v0.1.0).
- Server publication timestamp: 2026-11-02T12:31:17Z.
- Status confirmed through GitHub API: draft=false, prerelease=true, three attached assets uploaded.
- Fresh public Git history preserves reviewed source without exposing unreviewed local Git objects. Original local history remains preserved separately.

## Archive content and identity

| Asset | Bytes | Files | SHA-256 |
| --- | ---: | ---: | --- |
| h2physics-0.1.0-py3-none-any.whl | 1632165 | 371 | `0fccc59658f9cedd5479ef175069f1d41443e7ab05e252b71db572dc18cbd4b6` |
| h2physics-0.1.0.tar.gz | 5047511 | 1544 | `e274226e3ad3685d60dfe8b5337c4be77db3aac597f75bde8175059038e84f9e` |

GitHub's reported SHA-256 digests match these local values. Both archives contain all 365 package Python files with zero missing, unexpected or byte-different members against reviewed working sources. Both passed strict Twine checks. License/NOTICE, paths, credential markers and external-data exclusions passed the actual archive audit. Detailed output: [distribution audit](../research/release_audit.md).

The Git-bound snapshot audit inspected 1,543 files, including staged blobs and current content. The documentation path check inspected 5,309 local destinations across 499 Markdown files with zero missing paths before these post-publication receipt pages. These checks do not establish upstream rights or whole-model physical validity. Read [publication audit](PUBLICATION_AUDIT.md) for phrase-screen and license-review scope.

## Clean installed-wheel receipt

A new isolated Windows environment installed the built wheel, not an editable checkout. The smoke ran from a separate empty working directory with Python -I, and asserted that imports came from site-packages. pip check reported no broken requirements.

| Component | Installed version |
| --- | --- |
| Python | 3.12.16 |
| h2physics | 0.1.0 |
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| CoolProp | 8.0.0 |
| fluids | 1.3.1 |
| pip | 25.0.1 |

The documented calculations produced:

- Hydrogen at 200,000 Pa and 300 K: density 0.16144746212591646 kg/m³.
- Frozen-property reference pipe: mass flow 0.00021427484849277764 kg/s, converged root.
- Demonstration stack: H₂ production 0.0005182134828131087 mol/s and electric input 142.81659542670673 W.

The smoke checked import/version, a native CoolProp state, hydraulic result and electrochemical result. It is not an experimental validation of the pipe, stack or external engine physics. No new full regression or 78-family physical qualification is claimed.

## Separate services and follow-up

PyPI and Zenodo were subsequently published as recorded in the [registry/archive receipt](REGISTRY_ARCHIVE_RECEIPT_0_1_0.md) and [publication status](PUBLICATION_STATUS.md). Version DOI: 10.5281/zenodo.23886390. The following build-only run describes the earlier packaging checkpoint; it is not the later PyPI publishing run. A build-only Linux GitHub Actions run at the frozen tag completed successfully: [run 41445480727](https://github.com/lyullee/h2physics/actions/runs/41445480727), 2026-11-02T12:32:39Z. Source hygiene, wheel/source build, Twine metadata check, archive audit and artifact upload all passed. The publish job was skipped by the explicit publish_pypi=false input; no PyPI upload occurred. Linux CI archives have their own build timestamps and are separate from the reviewed local release assets.

Post-build reports and service receipts intentionally follow the frozen source tag. They do not retroactively enter its archives; reruns and rebuilds need their own version/hash receipts.
