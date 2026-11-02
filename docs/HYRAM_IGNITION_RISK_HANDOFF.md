# HyRAM ignition outcomes in conditional risk branches

`h2physics.adapters.hyram_ignition_risk.bind_hyram_ignition_to_risk()` maps
the existing HyRAM ignition result object into the repository's optional native
conditional-risk `Branch` and `RiskInput` objects. It contains no ignition
correlation and does not import or execute HyRAM. It does not evaluate the risk
request.

## Probability basis

HyRAM returns immediate and delayed ignition probabilities relative to one
release. The adapter retains those values and forms the complementary branch
`P(no ignition) = 1 - P(immediate) - P(delayed)`. These three outcomes form a
mutually exclusive and exhaustive branch partition conditional on the single
loss-of-containment event. The caller must supply the native loss-of-containment
`Frequency` object. The adapter retains that exact object and applies no
annual-rate, mission-time or Poisson conversion. Immediate and delayed values
are not divided by their sum or interpreted as probabilities conditioned on
ignition.

The caller also supplies a receptor ID, partition-evidence ID, three distinct
branch IDs, probability-factor IDs, three typed `ConditionalHarmBinding`
objects, and harm-factor IDs. Any additional native `Factor` objects are passed
explicitly by branch. The partition evidence ID must be added to the native risk
context, and the normal `conditional_risk()` input checks still apply to source,
receptor, harm, annual frequency, evidence, and partition.

```python
from h2physics.adapters import (
    ConditionalRiskNative,
    bind_hyram_ignition_to_risk,
)

native_risk = ConditionalRiskNative.from_installed()
binding = bind_hyram_ignition_to_risk(
    ignition_result, native_risk,
    frequency=caller_loc_frequency,
    receptor_id="receptor-17",
    partition_evidence_id="source-study-ignition-partition-v1",
    outcome_branch_ids={
        "no_ignition": "no-ignition",
        "immediate_ignition": "immediate-ignition",
        "delayed_ignition": "delayed-ignition",
    },
    probability_factor_ids={
        "no_ignition": ("no-ignition-factor",),
        "immediate_ignition": ("immediate-ignition-factor",),
        "delayed_ignition": ("delayed-ignition-factor",),
    },
    harm_bindings={
        "no-ignition": no_ignition_harm,
        "immediate-ignition": immediate_harm,
        "delayed-ignition": delayed_harm,
    },
    harm_factor_ids={
        "no-ignition": "no-ignition-harm",
        "immediate-ignition": "immediate-harm",
        "delayed-ignition": "delayed-harm",
    },
)
binding.require_current()
# Use binding.request with its original caller frequency and include the
# partition, table and harm evidence in the context before conditional_risk().
```

## Provenance and limitations

The result retains the caller's table identity/evidence/content digest, release
rate, HyRAM package version and native source hash. This is a lineage record,
not a cryptographic signature of the upstream evaluation. The synthetic
Hangang handoff case uses authored probability values and checks request and
identity contracts; it does not load HyRAM or prove the values came from an
executed HyRAM calculation.

The risk adapter does not infer LOC frequency, occupancy, event-tree factors,
harm probabilities, source-to-receptor transport or physical consequences.
Combined installation of the Apache-2.0 risk toolkit and separately installed
GPL-3.0-only HyRAM is not cleared by this object adapter. Any combined
distribution requires an independent license-compatibility review. See
`docs/HYRAM_IGNITION_PROBABILITY.md` and `docs/CONDITIONAL_RISK.md`.
