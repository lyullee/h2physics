"""Deferred synthetic contract for typed HyRAM-to-risk branch composition."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hyram-absolute-ignition-to-conditional-risk-branches",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_handoff",
        parameters={},
        invariants=(
            "release-relative-immediate-and-delayed-values-map-to-separate-LOC-branches",
            "no-ignition-is-the-explicit-complement-and-all-three-branches-sum-to-one",
            "the-exact-caller-frequency-object-is-preserved-without-rate-or-time-conversion",
            "branch-identities-factor-bases-harm-bindings-and-partition-evidence-are-required",
            "table-source-provider-version-and-module-hash-remain-in-the-handoff-lineage",
            "the-branch-handoff-does-not-import-or-execute-HyRAM-or-evaluate-risk",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import hashlib
    from dataclasses import replace
    import numpy as np

    from h2physics.adapters.conditional_risk import (
        ConditionalHarmBinding,
        ConditionalRiskNative,
    )
    from h2physics.adapters.hyram_ignition import (
        HyRAMIgnitionProbability,
        HyRAMIgnitionTable,
    )
    from h2physics.adapters.hyram_ignition_risk import bind_hyram_ignition_to_risk
    from h2physics.core import Origin

    native = ConditionalRiskNative.from_installed()
    contracts, risk = native.contracts, native.risk_module
    source_digest = contracts.digest({"annual_loc_rate": 1.e-4, "basis": "declared synthetic"})
    frequency = risk.Frequency(
        asset_id="synthetic-hydrogen-asset",
        scenario_id="synthetic-single-LOC",
        operating_case_id="synthetic-stationary-case",
        annual_frequency_per_year=1.e-4,
        origin="user_supplied",
        source_digest=source_digest,
        source_code_digest=hashlib.sha256(b"synthetic frequency contract").hexdigest(),
        evidence_ids=("synthetic-loc-frequency-evidence",),
    )
    table = HyRAMIgnitionTable(
        table_id="synthetic-h2-rate-table",
        fuel_species="h2",
        flow_thresholds_kg_s=(0.1,),
        immediate_probability=(0.02, 0.06),
        delayed_probability=(0.01, 0.04),
        evidence_id="synthetic-hyram-table-evidence",
        origin=Origin.SYNTHETIC,
    )
    result = HyRAMIgnitionProbability(
        table=table,
        release_rate_kg_s=0.2,
        immediate_probability=0.06,
        delayed_probability=0.04,
        total_probability=0.10,
        hyram_version="synthetic-6.x",
        native_module_sha256="a" * 64,
        native_module_path="synthetic-provider-path",
    )
    receptor_id = "synthetic-risk-receptor"
    branch_ids = {
        "no_ignition": "no-ignition",
        "immediate_ignition": "immediate-ignition",
        "delayed_ignition": "delayed-ignition",
    }
    harm = {
        branch_id: ConditionalHarmBinding(
            probability,
            receptor_id,
            "synthetic-frame",
            "synthetic-clock",
            (0., 1.),
            "synthetic-source",
            response_model,
            (0., 0., 0.),
            (evidence_id,),
            Origin.SYNTHETIC,
        )
        for branch_id, probability, response_model, evidence_id in (
            ("no-ignition", 0., "declared-zero-harm", "zero-harm-evidence"),
            ("immediate-ignition", .7, "declared-immediate-harm", "immediate-harm-evidence"),
            ("delayed-ignition", .5, "declared-delayed-harm", "delayed-harm-evidence"),
        )
    }
    probability_ids = {
        "no_ignition": ("hyram-no-ignition-factor",),
        "immediate_ignition": ("hyram-immediate-factor",),
        "delayed_ignition": ("hyram-delayed-factor",),
    }
    harm_ids = {branch_id: f"harm-{branch_id}" for branch_id in branch_ids.values()}
    binding = bind_hyram_ignition_to_risk(
        result,
        native,
        frequency=frequency,
        receptor_id=receptor_id,
        partition_evidence_id="synthetic-LOC-ignition-partition",
        outcome_branch_ids=branch_ids,
        probability_factor_ids=probability_ids,
        harm_bindings=harm,
        harm_factor_ids=harm_ids,
    )
    binding.require_current()
    observed = {
        branch.id: branch.conditional_probability
        for branch in binding.request.branches
    }
    expected = {"no-ignition": .9, "immediate-ignition": .06, "delayed-ignition": .04}
    if observed != expected:
        raise AssertionError(f"Release-relative ignition partition changed: {observed}")
    if binding.request.frequency is not frequency or binding.frequency is not frequency:
        raise AssertionError("The caller-owned loss-of-containment Frequency was replaced")
    if (binding.partition_evidence_id != binding.request.partition_basis
            or any(branch.probability_basis != binding.partition_evidence_id
                   for branch in binding.request.branches)):
        raise AssertionError("Branch partition evidence was not retained")
    if (binding.table_id != table.table_id
            or binding.table_evidence_id != table.evidence_id
            or binding.table_sha256 != table.content_sha256
            or binding.native_module_sha256 != result.native_module_sha256
            or binding.hyram_version != result.hyram_version):
        raise AssertionError("HyRAM table/provider lineage was not retained")
    try:
        replace(binding, outcome_probabilities={**binding.outcome_probabilities,
                                                "no_ignition": .8})
    except (TypeError, ValueError):
        mutation_rejected = True
    else:
        raise AssertionError("Changed branch probability was admitted")
    try:
        replace(binding, lineage_sha256="b" * 64)
    except (TypeError, ValueError):
        lineage_mutation_rejected = True
    else:
        raise AssertionError("Changed lineage digest was admitted")
    from h2physics.adapters.hyram_ignition_risk import _nonnegative, _probability
    for boolean_probability in (True, np.bool_(True)):
        try:
            _probability(boolean_probability, "boolean probability")
        except ValueError:
            pass
        else:
            raise AssertionError("A boolean probability was accepted as a number")
        try:
            _nonnegative(boolean_probability, "boolean release rate")
        except ValueError:
            pass
        else:
            raise AssertionError("A boolean release rate was accepted as a number")
    return ValidationOutcome(True, {
        "branch_probabilities_conditional_on_LOC": observed,
        "caller_frequency_per_year": frequency.annual_frequency_per_year,
        "frequency_identity_preserved": True,
        "hyram_table_sha256": binding.table_sha256,
        "hyram_provider_sha256": binding.native_module_sha256,
        "lineage_sha256": binding.lineage_sha256,
        "mutation_rejected": mutation_rejected,
        "lineage_mutation_rejected": lineage_mutation_rejected,
    }, (
        "Synthetic handoff contract only; the HyRAM result values are authored test data, not a native HyRAM evaluation.",
        "No facility frequency, conditional-on-ignition probability, harm model or physical consequence is inferred.",
    ))
