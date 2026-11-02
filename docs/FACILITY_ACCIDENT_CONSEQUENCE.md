# Facility accident to consequence handoff

`h2physics.adapters.run_facility_accident_consequence()` composes the prepared
finite-operation → source admission → preferred-dispersion chain with the existing
caller-owned consequence evaluator. It executes the chain first and passes the
same admitted `FacilityDispersionHandoff` object to the receiver. The returned
`FacilityAccidentConsequenceRun` retains the original graph result, handoff, and
`FacilityConsequenceEvaluation` receipt and rechecks their ownership and freshness.

```python
from h2physics.adapters.facility_accident_consequence import (
    run_facility_accident_consequence,
)

run = run_facility_accident_consequence(
    prepared_chain,
    consequence_owner,
    method_evidence_id="documented-method-and-applicability",
)
run.require_current()
```

The receiving owner still defines its own typed result and must retain the exact
handoff through `facility_handoff` and implement `require_current()`. Existing
acceptance gates remain authoritative: a failed chain never calls the receiver;
a receiver exception, changed callback configuration, stale handoff or invalid
result raises `FacilityAccidentConsequenceError`, with the completed chain result
and failure stage retained when available. Such failures are not converted into a
success receipt.

This is orchestration only. It does not calculate plume exposures, choose receptors
or thresholds, interpret a concentration or radiation field, infer harm probability,
or add annual frequency. Consequence law, spatial mapping and applicability remain
the receiving owner's responsibilities. The authored deferred case checks identity
and failure preservation using a synthetic native-result fixture; it is not evidence
for a physical consequence method. Execution is enrolled in the
`facility-protection` Nurion profile and remains deferred.
