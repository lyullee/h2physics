"""Deferred relief-to-line native contract for the later Nurion validation batch."""

from h2physics.adapters.relief_cooldown_interface import (
    ReliefCooldownInterfaceError,
    bind_relief_cooldown_sequence,
    bind_relief_to_line_cooldown,
)
from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="relief-line-cooldown-common-clock-interface",
        profile="lh2dt-operation",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "retained relief samples and dynamic cooldown audit share one declared clock window",
            "interface release totals equal native retained mass and enthalpy samples",
            "directly constructed receipts cannot invent relief totals or decreasing inlet mass",
            "relief native traces cannot be directly constructed or cloned as accepted runs",
            "evidence identifiers must be passed as complete IDs rather than iterated characters of a string",
            "relief and line ports retain matching absolute-pressure phase/property bases and separate evidence",
            "post-bind tolerance and evidence changes cannot relax or relabel the closure receipt",
            "the interface never claims solver coupling or phase transformation",
        ),
    ), ValidationCase(
        identifier="relief-line-cooldown-segment-composition",
        profile="lh2dt-operation",
        entrypoint=__name__ + ":validate_segment_composition",
        parameters={},
        invariants=(
            "phase-specific receipts share original relief/cooldown runs, ports and property bases",
            "segments meet at the exact retained event-time sample without duplicated output time",
            "cumulative release and line-inlet mass/enthalpy remain continuous across boundaries",
            "gaps and overlaps between segment windows are rejected",
            "composition preserves per-segment evidence and freshness",
        ),
    ),)


def evaluate(relief_trace, cooldown_audit, boundary_histories):
    """Bind explicit line inlet samples to one native tank release trace."""
    return bind_relief_to_line_cooldown(
        relief_trace,
        cooldown_audit,
        time_s=boundary_histories.time_s,
        line_inlet_mass_kg=boundary_histories.mass_kg,
        line_inlet_enthalpy_j=boundary_histories.enthalpy_j,
        boundary_id=boundary_histories.boundary_id,
        evidence_ids=boundary_histories.evidence_ids,
        relief_port=boundary_histories.relief_port,
        line_port=boundary_histories.line_port,
        mass_tolerance_kg=boundary_histories.mass_tolerance_kg,
        enthalpy_tolerance_j=boundary_histories.enthalpy_tolerance_j,
    )


def validate_contract(*, work_directory, **parameters):
    del work_directory
    from dataclasses import replace

    scenario = parameters["scenario"]
    receipt = evaluate(**scenario)
    receipt.require_current()
    from h2physics.adapters.lh2dt_relief import ReliefTankTrace
    relief_fields = {
        name: getattr(receipt.relief, name)
        for name in ReliefTankTrace.__dataclass_fields__
        if name != "_issuer_token"
    }
    unissued_relief_rejections = 0
    for construct in (
        lambda: ReliefTankTrace(**relief_fields),
        lambda: replace(receipt.relief, time_s=receipt.relief.time_s.copy()),
    ):
        try:
            construct()
        except TypeError:
            unissued_relief_rejections += 1
    assert unissued_relief_rejections == 2
    forged_rejected = False
    forged_mass = receipt.relief_mass_kg.copy()
    forged_mass[-1] += 1.
    try:
        replace(receipt, relief_mass_kg=forged_mass)
    except ReliefCooldownInterfaceError:
        forged_rejected = True
    assert forged_rejected
    string_evidence_rejected = False
    try:
        replace(receipt, evidence_ids="single-evidence-string")
    except ReliefCooldownInterfaceError:
        string_evidence_rejected = True
    assert string_evidence_rejected
    original_tolerance = receipt.mass_tolerance_kg
    object.__setattr__(receipt, "mass_tolerance_kg", original_tolerance + 1.0)
    stale_tolerance_rejected = False
    try:
        receipt.require_current()
    except ReliefCooldownInterfaceError as error:
        stale_tolerance_rejected = "tolerances" in str(error)
    assert stale_tolerance_rejected
    object.__setattr__(receipt, "mass_tolerance_kg", original_tolerance)
    original_evidence = receipt.evidence_ids
    object.__setattr__(receipt, "evidence_ids", (*original_evidence, "replacement-evidence"))
    stale_evidence_rejected = False
    try:
        receipt.require_current()
    except ReliefCooldownInterfaceError as error:
        stale_evidence_rejected = "evidence" in str(error)
    assert stale_evidence_rejected
    object.__setattr__(receipt, "evidence_ids", original_evidence)
    assert receipt.require_current() is receipt
    phase_mismatch_rejected = False
    wrong_phase_port = replace(receipt.line_port, phase=(
        "gas" if receipt.relief_port.phase != "gas" else "liquid"))
    try:
        replace(receipt, line_port=wrong_phase_port)
    except ReliefCooldownInterfaceError:
        phase_mismatch_rejected = True
    assert phase_mismatch_rejected
    return ValidationOutcome(
        True,
        {"scenario_id": scenario["boundary_histories"].boundary_id,
         "retained_samples": receipt.time_s.size,
         "unissued_relief_trace_rejections": unissued_relief_rejections,
         "forged_native_release_rejected": forged_rejected,
         "string_evidence_rejected": string_evidence_rejected,
         "stale_tolerance_rejected": stale_tolerance_rejected,
         "stale_evidence_rejected": stale_evidence_rejected,
         "phase_mismatch_rejected": phase_mismatch_rejected},
        ("Boundary ledger only; no coupled relief/cooldown simulation",),
    )


def validate_segment_composition(*, work_directory, **parameters):
    del work_directory
    scenario = parameters["scenario"]
    whole = evaluate(**scenario)
    if whole.time_s.size < 3:
        raise ValueError("Segment composition contract requires at least three retained relief samples")
    split = whole.time_s.size // 2

    def bind_slice(start, stop):
        return bind_relief_to_line_cooldown(
            whole.relief, whole.cooldown,
            time_s=whole.time_s[start:stop],
            line_inlet_mass_kg=whole.line_inlet_mass_kg[start:stop],
            line_inlet_enthalpy_j=whole.line_inlet_enthalpy_j[start:stop],
            boundary_id=whole.boundary_id,
            evidence_ids=whole.evidence_ids,
            relief_port=whole.relief_port, line_port=whole.line_port,
            mass_tolerance_kg=whole.mass_tolerance_kg,
            enthalpy_tolerance_j=whole.enthalpy_tolerance_j,
        )

    left, right = bind_slice(0, split+1), bind_slice(split, whole.time_s.size)
    sequence = bind_relief_cooldown_sequence((left, right))
    sequence.require_current()
    import numpy as np

    assert np.array_equal(sequence.time_s, whole.time_s)
    assert len(sequence.phase_intervals) == 2
    overlap_rejected = False
    try:
        bind_relief_cooldown_sequence((left, bind_slice(split-1, whole.time_s.size)))
    except ReliefCooldownInterfaceError as error:
        overlap_rejected = "event-time" in str(error)
    assert overlap_rejected
    return ValidationOutcome(
        True,
        {"composed_segments": len(sequence.segments), "unique_retained_samples": len(sequence.time_s),
         "overlap_rejected": overlap_rejected},
        ("Per-segment caller phase/evidence qualification only; no flow routing or solver coupling",),
    )


__all__ = ["ReliefCooldownInterfaceError", "cases", "evaluate", "validate_contract"]
