# Development contract

Read README.md, docs/ARCHITECTURE.md, docs/RIGHTS_AND_PROVENANCE.md,
docs/DEVELOPMENT_HISTORY.md and docs/RESEARCH_CONTINUATION.md before changes.

- Public Python APIs carry explicit SI units, material identity, caloric reference and clocks.
- Use CoolProp or a table qualified against that native provider for fluid properties. Do not silently substitute an EOS.
- Keep optional providers separately installed with their own licenses and qualified revisions. Never fake accepted native results or bypass applicability gates.
- External raw observations, reference documents, installed engines, private configuration and execution artifacts are excluded from public Git and distributions.
- Write original explanations and implementation. Preserve scientific attribution, source/version/checksums and rights evidence. Rewording alone is not rights clearance.
- Separate implementation, input checks, numerical verification, connection tests, calibration and held-out experimental comparison. Do not infer a broad qualification from a narrower passing case.
- Keep failed/rejected results and explicit unavailable-provider states. Missing test evidence is not missing implementation.
- Prefer bounded existing regression tests and representative examples; expand validation only to match the requested scope.
- Independent native-engine physics and whole-facility qualification are separate research tasks, not automatic consequences of adapter tests.
- Before publication audit the exact source snapshot and both built archives, then smoke-test the installed wheel outside the checkout.
- Update API documentation, development/continuation records and evidence summaries with material changes. Never claim unexecuted tests or unpublished releases.
- Write UTF-8 text atomically where practical; preserve user-owned work and local history.
