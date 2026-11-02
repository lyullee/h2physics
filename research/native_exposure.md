# Conditional supplied-field native exposure verification

Reproduce: `python scripts/check_hyram_exposure.py --hyram-packages artifacts/native_hyram_packages`.

Actual HyRAM6.1,SciPy1.16.3,NumPy2.5.4; native/analytic/invalid cases took 0.0885698s. Native GPL-3.0-only implementation, coefficients and datasets are separately installed and unchanged.

All fields/model choices/receptor coordinates are original numerical fixtures, not measured receptor vulnerability. Every result is conditional-on-supplied-exposure. No source/Flame/blast or accepted accident chain, participant count, occurrence probability or annual frequency is inferred; existing source-to-Flame rejection remains rejected.

Native dose/probit/CDF calls are actual functions, not copied formulas or a replacement solver. Input units are incident/absorbed radiant W/m2, pressure gaugePa and positive impulsePa*s. Absorbed mathematical dose has no native harm probability. Canonical model IDs and the native normal mean convention are explicitly selected, with caller-declared applicability/evidence that this replay does not independently qualify.

| Actual thermal model at40000W/m2 for10s | Native probability |
|---|---:|
| eise | 0.0784557581622 |
| tsao | 0.75315901703 |
| tno | 0.43426121331 |
| lees | 0.0034584963625 |

| Check | Value |
|---|---:|
| constant native dose (W/m2)^(4/3)s | 13679807.5734 |
| pulse dose / equal-fluence smooth dose | 1.25992104989 |
| common pulse/smooth radiant fluence J/m2 | 200000 |
| constant wrapper probability error | 0 |
| independent normal CDF error | 1.38777878078e-17 |
| native held splitting relative error | 0 |
| linear analytic power-integral relative error | 2.44249065418e-15 |
| native linear subdivision relative error | 0 |
| signed triangle positive impulse Pa*s | 5000 |
| peak-only native model probability | 0.0054531772084 |
| native convenience wrapper with unused zero impulse | 0 |

Held histories sum native interval doses under an explicit additive/no-recovery equivalent-dose assumption. The pulse uses40000W/m2 for5s thenzero5s; the equal-fluence smooth history uses20000W/m2 for10s. Linear12000→36000W/m2 over6s calls native unit-time dose inside SciPy quadrature; the independent mathematical power integral and16-segment native refinement agree. No effective averaged flux is invented. Biological recovery, movement/escape and calibration of time-varying harm remain outside this constitutive reduction.

The linear pressure waveform at times100,100.05,100.1,100.15s has gaugePa0,100000,0,−20000. Its positive triangle impulse is5000Pa*s; the negative phase remains in the original input. The chosen native impact models require both summaries; missing impulse is retained as an error. For native peak-only models no unused impulse is supplied to the selected native function. The existing native convenience wrapper would force zero when given an irrelevant zero impulse; that actual discrepancy is recorded without altering native code/model.

| Actual pressure model at100000Pa and5000Pa*s | Native probability |
|---|---:|
| leis | 0.0054531772084 |
| lhse | 0.551716786655 |
| head | 0.949543564969 |
| coll | 0.93211389004 |

| Retained failed input | Native calls returned | Native failed-call pending | Original cause |
|---|---:|---|---|
| masked supplied sample | 0 | False | ValueError: Missing/masked/nonfinite history is retained without filling |
| unmasked nonfinite sample | 0 | False | ValueError: Missing/masked/nonfinite history is retained without filling |
| negative heat | 0 | False | ValueError: Thermal dose needs a nonnegative declared radiant-flux history |
| absorbed is not incident | 0 | False | ValueError: Native thermal harm requires incident flux; absorbed dose is a separate diagnostic |
| unknown model | 0 | False | ValueError: Choose a canonical native model and its declared normal-mean convention |
| wrong normal convention | 0 | False | ValueError: Choose a canonical native model and its declared normal-mean convention |
| missing impact impulse | 0 | False | ValueError: Chosen native pressure model requires supplied positive-phase impulse |
| native dose overflow | 0 | True | OverflowError: (34, 'Result too large') |
| native dose underflow | 1 | False | ValueError: Positive native thermal dose underflow is unresolved |
| native collapse arithmetic limit | 0 | True | OverflowError: (34, 'Result too large') |

The exact input/selection, actual native module/function references, returned raw-call prefix, pending failed-call args, quadrature records and original cause remain available. No missing sample, negative heat, numeric underflow or absent impulse is filled. Native zero exposure uses its actual wrapper; the unexposed intermediate probit is None. Native CDF saturation at0/1 is numerical response, not measured certainty. Normal-mean rebinding is rejected; no native monkeypatch or copied coefficient table is used.

The public owner verify_result API reexecutes the existing native path and returns the original result object on success. Input/model/mean/evidence/tolerance/response-kind/native-source identity is bound separately from the computed summaries. It compares probability,dose,probit,fluence,pressure/impulse and actual native function/argument/raw-call records, including raw-result object binding to its retained native call. Concrete owner type is required; structural lookalikes are not computed-native provenance. QUADPACK comparisons use only integral/error, counts, active subintervals and active error-order pointers; unused uninitialized work-array tails are ignored and a deliberate tail rewrite still verifies.

| Rejected cached record | Actual replay available | Original verification cause |
|---|---|---|
| probability .9 | True | Exposure native replay differs in probability |
| different native model | False | Exposure input/model/mean/evidence/settings identity changed |
| different mean | False | Exposure input/model/mean/evidence/settings identity changed |
| different model evidence | False | Exposure input/model/mean/evidence/settings identity changed |
| detached raw native probability | True | Exposure native probability is detached from its actual native call |
| mutually replaced native call and probability | True | Exposure native replay differs in probability |
| different input source | False | Exposure input/model/mean/evidence/settings identity changed |
| different chain status | False | Exposure native source/module/status identity differs |
| different native source | False | Exposure native source/module/status identity differs |
| structural fake | False | Native exposure verification requires an actual ExposureResult |

| Verification gate | Pass |
|---|---|
| actual native HyRAM6.1 functions retained | True |
| all four thermal models match actual constant native wrapper | True |
| independent normal CDF error <1e-14 | True |
| piecewise held pulse dose law differs from equal fluence | True |
| held interval splitting preserves native dose <1e-14 | True |
| independent linear power integral <3e-14 relative | True |
| linear-history subdivision refinement <3e-14 relative | True |
| absorbed diagnostic has no implicit harm response | True |
| signed pressure triangle has explicit positive impulse | True |
| all four pressure models match genuine native summary response | True |
| peak-only unused-zero native anomaly is exposed | True |
| native zero exposure branch retained | True |
| ten invalid/missing/native numeric cases retain original input/cause | True |
| normal-mean owner binding cannot be silently redirected | True |
| owner verifies actual native records returning original identity | True |
| owner rejects ten altered summaries/model/raw/source/structural records | True |
| probability .9 rejection retains actual native replay | True |
| native quadrature inactive workspace tails are ignored | True |
| conditional source/clock/receptor status remains explicit | True |
| host/test/script/docs unchanged | True |
| native source/license/metadata/numerical engines unchanged | True |
| new host inputs are LF text | True |

Primary sources: [official native probit API/source](https://github.com/sandialabs/hyram/blob/master/src/hyram/qra/probits.py), [Sandia HyRAM/versioned documentation](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/), [HyRAM6.1 metadata](https://pypi.org/project/hyram/6.1/), [technical manual bibliographic reference](https://doi.org/10.2172/2563814). Installed6.1source/API/GPL notice and public source were inspected; manual download endpoints timed out during this review. Original harm-calibration data/table rights and independent human-response validation were not reviewed or supplied. No table/coefficients are redistributed.

## Source fingerprints

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/hyram_exposure.py | 2fbfa2ce6fea1ffade397ae75f17221dc45ef96d984137c416d05c959a7ea9cf | 2fbfa2ce6fea1ffade397ae75f17221dc45ef96d984137c416d05c959a7ea9cf |
| tests/test_hyram_exposure.py | e5d3cfdc08deca2349b68854f6cc9fdc5001180b5a87d862a1b8cf2215f2f161 | e5d3cfdc08deca2349b68854f6cc9fdc5001180b5a87d862a1b8cf2215f2f161 |
| scripts/check_hyram_exposure.py | ec3fe724ad33c54d1a93ff9ab98bfb7ec4507bb523ff516036a220c0da123b41 | ec3fe724ad33c54d1a93ff9ab98bfb7ec4507bb523ff516036a220c0da123b41 |
| docs/NATIVE_EXPOSURE.md | f089e954c41728046c986494a90265fe3f32e961bf4429bc9cd8e7f3f6a49ca6 | f089e954c41728046c986494a90265fe3f32e961bf4429bc9cd8e7f3f6a49ca6 |
| src/h2physics/core.py | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 |

| Installed input | Begin SHA256 | End SHA256 |
|---|---|---|
| HyRAM probits | 7cd64f7b5166ac1cd92b2afe07ee1409ac07df302129e80bd63f7bca006cc770 | 7cd64f7b5166ac1cd92b2afe07ee1409ac07df302129e80bd63f7bca006cc770 |
| HyRAM utility | fae9625b1735c9e135d43b2bcc53652134b628e52d38f75a49779e1cd74c1c1e | fae9625b1735c9e135d43b2bcc53652134b628e52d38f75a49779e1cd74c1c1e |
| HyRAM GPL notice | 3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4 | 3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4 |
| HyRAM metadata | 639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52 | 639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52 |
| SciPy distributions | f49b5bbf66a2530661f841240aea310c9eb95c7efff1e19302b8e4005be17f5d | f49b5bbf66a2530661f841240aea310c9eb95c7efff1e19302b8e4005be17f5d |
| SciPy distribution infrastructure | bb4c93d1b48d6e97e609b81d3e5930f962eed85014a70a5da12bd244388024fd | bb4c93d1b48d6e97e609b81d3e5930f962eed85014a70a5da12bd244388024fd |
| SciPy special compiled functions | 9b0c944609c4e2e234e9750474089dc398d18c639b6c355204e6573dad7fe69d | 9b0c944609c4e2e234e9750474089dc398d18c639b6c355204e6573dad7fe69d |
| SciPy quadrature compiled engine | 13a10765c2f5b6165f2c95f1779b8ce7b41e59edc9a7630e9568709ab37ed50a | 13a10765c2f5b6165f2c95f1779b8ce7b41e59edc9a7630e9568709ab37ed50a |
