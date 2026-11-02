# Common-cause-aware k-of-n detector reliability

`h2physics.detector_reliability.evaluate_kofn_detector_reliability` calculates
the probability that fewer than `k` detectors alarm during one declared mission.
It supports heterogeneous per-detector failure probabilities without assuming
identical channels. A separately supplied common-cause event disables the
entire voting group.

The per-channel probabilities are conditional independent failure probabilities
over the supplied mission, conditional on no modeled common cause. If `q_i` is
the conditional failure probability for channel `i`, `C` the common-cause event
probability and `P_ind` the exact Poisson-binomial probability of fewer than `k`
alarms, the total fail-to-alarm probability is

`P_system = C + (1 - C) P_ind`.

The model records the ordered detector IDs, one evidence identity per channel
probability, voting logic, mission duration and separate common-cause evidence.
It does
not infer failure rates, beta factors, common-cause groups, setpoints, repair,
proof-test interval, alarm latency or input probabilities. Use probabilities
whose event basis and mission duration match the declared identity.

```python
assessment = evaluate_kofn_detector_reliability(
    ("north", "south", "roof"), (0.02, 0.04, 0.03),
    votes_required=2,
    common_cause_failure_probability=0.005,
    mission_duration_s=3600.0,
    system_id="compressor-hall-h2-detection",
    mission_id="one-hour-demand-window",
    voting_logic_id="two-out-of-three",
    independent_probability_evidence_ids=("north-demand-data-v2", "south-demand-data-v4", "roof-demand-data-v1"),
    common_cause_evidence_id="shared-power-and-environment-review-v1",
)
```

The deferred Hangang case uses synthetic values to check the heterogeneous
Poisson-binomial and common-cause combination. It is an algebraic contract, not
a detector qualification or SIL assessment.

## Versioned empirical trial evidence

When simultaneous same-duration detector demand outcomes are available, use
`record_kofn_trial_evidence(...)` followed by `summarize_kofn_trials(...)`.
The evidence binds ordered detector IDs, unique demand-window IDs, boolean
outcomes, vote logic, mission duration, source ID/version/SHA-256, and the
caller-declared trial design ID. `require_current()` checks its sealed content;
outcome arrays are immutable and direct construction/cloning is rejected.

This route computes observed frequencies directly from simultaneous system
outcomes, so it does not assume independent detector channels. A row is one
equal-duration demand window. A common-cause outage must mark all channels as
failed. The source hash is attached as caller-supplied provenance: the API does
not open or rehash the source file. Frequencies are descriptive sample ratios.
The separate exact interval below is available only when the caller supplies
sampling-independence evidence; neither the reader nor the frequency summary
establishes that condition. Mission-rate extrapolation and source-file checksum
verification remain with the caller.

## Exact interval for declared independent demand windows

`interval_for_kofn_trials(evidence, ...)` adds a two-sided Clopper–Pearson
binomial interval for one selected outcome: system fail-to-alarm, common-cause
outage, or conditional fail-to-alarm among non-common-cause windows. The
function requires an `independence_evidence_id` supplied by the caller. That
identity documents the sampling argument; the software cannot determine
whether recorded windows are independent, identically designed, representative,
or free of selection bias. Conditional intervals omit common-cause windows from
their denominator.

The interval is conditional on the binomial sampling model and applies to the
declared demand-window probability. It is not an annualized rate, future field
reliability, repair/proof-test estimate, confidence statement about source
provenance, or SIL assessment. Repeated or correlated demand windows require an
appropriate dependence model instead of this interval.

The interval uses equal-tailed exact binomial limits as introduced by Clopper
and Pearson ([Biometrika, 1934](https://doi.org/10.1093/biomet/26.4.404)); beta
quantiles are evaluated with SciPy. The synthetic Hangang contract checks the
count-to-interval mapping and rejection boundaries. No field detector sample
has been independently qualified, and this model level remains
`implemented_unverified`.
