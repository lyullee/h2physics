# h2physics 0.2.0: release scope and verification handoff

Prepared on 2026-11-03 for an Alpha research-software update. This document
distinguishes already executed model/software checks from the new version's
distribution and service-publication gates. Preparation does not assert a PyPI
upload, a published Zenodo version or an issued new DOI. See
[current publication status](PUBLICATION_STATUS.md) for confirmed outcomes.

## Source and change boundary

The numerical implementation and model-level evidence originate at the tested
development checkpoint
[`13a4f6068c560a7425ffdf500d86a8eedec6986a`](https://github.com/lyullee/h2physics/commit/13a4f6068c560a7425ffdf500d86a8eedec6986a).
The 0.2.0 preparation updates version metadata, citation/publication text and
registry-rendered README links. It changes no equations, constitutive defaults,
native provider choices or empirical calibration. The final release commit/tag
is frozen after these edits and recorded in the publication receipt; the earlier
development commit is not relabeled as that final source.

The package remains Alpha under Apache-2.0 for original code/documentation.
Optional providers remain separately installed under their own licenses.
The public 0.1.0 tag, PyPI file objects and version DOI
[10.5281/zenodo.23886390](https://doi.org/10.5281/zenodo.23886390) are preserved.
The existing concept DOI
[10.5281/zenodo.23886389](https://doi.org/10.5281/zenodo.23886389) identifies the
version series. No new version DOI is inferred from that concept identifier.

## Included model levels

These are eight work packages inside existing subject areas, not eight newly
qualified physical models or an expanded family-accuracy denominator.

| Work package | Implemented level | Remaining interpretation boundary |
| --- | --- | --- |
| R1 | Native HyRAM indoor accumulation and enclosure peaks | Hypothetical ignition-delay axis, not a blast waveform; [manual](INDOOR_AND_DDT.md) |
| R2 | Mixture expansion and evidence-bound FA/DDT screening | Necessary conditions with domains/uncertainty, not transition probability; [manual](INDOOR_AND_DDT.md) |
| R3 | CoolProp finite-stock expansion, disjoint energy allocation and weak-wave load reference | Explicit supplied conversion/shape and acoustic domain, not general near-field rupture or BLEVE; [manual](MECHANICAL_LOADS.md) |
| R4 | Linear generalized structural dynamics | Supplied differential-pressure history and generalized parameters, not plastic failure or a building certificate; [manual](MECHANICAL_LOADS.md) |
| R5 | Actual TESPy power/liquefaction networks, ExerPy physical exergy and cycle-to-stack example | Explicit utility and generator boundaries, not an inferred complete cold-box electric load; [power manual](THERMAL_CYCLES_AND_REDOX.md), [liquefaction manual](LIQUEFACTION_CYCLE.md) |
| R6 | Native finite gas/two-solid redox equilibrium and reaction/heat mapping | Restricted phases and supplied kinetic/material evidence; [manual](THERMAL_CYCLES_AND_REDOX.md) |
| R7 | Electrode iR, Tafel, product/charge, Faradaic-efficiency and site-turnover analysis | Supplied measurement/reference/site basis, not mechanistic proof; [manual](ELECTROCATALYST_METRICS.md) |
| R8 | Coupled PAR draft, gas/catalyst heat, species and entropy balances | Declared device-capacity law/domain, not intrinsic surface kinetics or device qualification; [manual](PAR_DEVICE.md) |

CoolProp owns nonreacting fluid properties; Cantera owns reacting thermochemistry
and native phase equilibrium. TESPy/ExerPy own their network/component kernels.
The update reuses these owners and existing finite-reaction/stack interfaces.
No native solver tree, source reference asset, raw measurement payload, private
configuration or credentials are included as a release asset. Scientific
attribution and dependency notices remain available. A release-content audit is
not a universal legal clearance.

## Existing executed software evidence

The detailed [extension record](ENHANCEMENTS_20261102.md) retains commands,
dependency profiles, failed attempts, corrections and model-specific limits.
Its completed scope is:

| Evidence | Recorded outcome | Counting and scope |
| --- | --- | --- |
| New checks | 92 distinct cases | 91 model/interface cases plus one fresh-process optional-dependency regression |
| Related existing checks | 47 distinct cases | Selected multiphase/caloric, electrochemistry, core-thermo and cold imports |
| Installed development wheel, main profile | 137 passed, 2 skipped | Ran outside the source checkout; two genuine HyRAM cases need the separate native profile |
| Installed development wheel, HyRAM profile | 9 passed | Two omitted cases completed; seven repeated input checks are not added again |
| Combined selected scope | 139 distinct cases completed | No unresolved failure in this focused scope; not a full catalogue qualification |
| Executable manuals | Eight Python blocks across six manuals completed | Authored demonstrations and host/native connections, not experimental device data |
| GitHub model-extension CI | Both jobs successful | [Run 41471065252](https://github.com/lyullee/h2physics/actions/runs/41471065252) at the development checkpoint |

The broader 414-case control remains **348 passed, 61 failed, 5 skipped**, with
identical outcomes before and after the extension. The failures involve
unavailable optional providers or ignored local campaign artifacts. They remain
explicit reproducibility blockers, not passes. Independent native-engine
internal physics and complete-facility validation were outside this task.

The development wheel's recorded scientific environment was Python 3.12,
NumPy 2.5.4, SciPy 1.18.1, CoolProp 8.0.0, Cantera 3.2.0, TESPy 0.11.3 and
ExerPy 0.2.0. The consistently selected HyRAM+ 6.1 profile used SciPy 1.16.3.
Fresh installation found and corrected an unrelated eager workbook import and
a native Windows non-ASCII mechanism-file lookup issue. The corrections and
negative cases remain in the manuals/tests rather than being hidden as skips.

## Required 0.2.0 distribution and service receipts

The preceding evidence belongs to the 0.2.0.dev0 implementation checkpoint.
Promoting the version does not itself establish that new archive objects are
correct. Complete and retain the following gates for the final 0.2.0 source:

1. Freeze the reviewed source revision and new tag; preserve all older tags.
2. Audit staged/current Git content and actual wheel/source archives, including
   all package Python members against the final source and license/data rules.
3. Check strict distribution metadata and install the actual new wheel outside
   the checkout; verify import/metadata version and representative calculations.
4. Publish through the existing scoped GitHub PyPI publisher, then retrieve both
   public registry files and verify their reported hashes and frozen Git source.
5. Install the actual registry version and check its selected examples/dependencies.
6. Publish a new Zenodo version in the existing concept series with actual
   author, version, license, source identity and reviewed files/checksums.
7. Verify public Zenodo state and downloaded file hashes, then update citation
   metadata and current publication records using the issued version DOI.

No archive hash, upload timestamp, final source revision, new workflow result or
new version DOI is fabricated here. Post-publication receipts may follow the
frozen tag on main; they do not retroactively change its archive contents.
