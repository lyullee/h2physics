"""Deferred static compressor anti-surge admission contracts."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="compressor-anti-surge-boundary-support",
            profile="compressor-map",
            entrypoint=__name__ + ":validate_boundary_support",
            invariants=("interpolate only between caller supplied surge points",
                        "reject corrected speed extrapolation"),
        ),
        ValidationCase(
            identifier="compressor-anti-surge-margin-native-replay",
            profile="compressor-map",
            entrypoint=__name__ + ":validate_native_margin_replay",
            invariants=("consume original native map traces",
                        "admit a point above the declared flow margin",
                        "retain and reject an insufficient-margin point",
                        "reject detached feasibility summaries",
                        "do not alter native compressor results"),
        ),
    )


def _boundary():
    from h2physics.adapters.compressor_anti_surge import (
        SurgeBoundary, SurgeBoundaryEvidence, SurgeLinePoint,
    )

    evidence = SurgeBoundaryEvidence("authored-static-surge-boundary",
        "urn:h2physics:authored-static-surge-boundary", "CC0-1.0", "0"*64)
    return SurgeBoundary("authored-boundary", (
        SurgeLinePoint(100.0, 0.01), SurgeLinePoint(200.0, 0.02),
    ), evidence)


def validate_boundary_support(*, work_directory, **parameters):
    del work_directory, parameters
    boundary = _boundary()
    assert boundary.flow_at(150.0) == 0.015
    rejected = 0
    for speed in (99.0, 201.0):
        try:
            boundary.flow_at(speed)
        except ValueError:
            rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"interpolated_surge_flow_kg_s": 0.015,
                                   "out_of_support_rejections": rejected},
        ("Authored line only; no machinery or manufacturer performance is qualified.",))


def validate_native_margin_replay(*, work_directory, **parameters):
    del work_directory
    from examples.lh2dt_compressor import build_stage
    from h2physics.adapters.compressor_anti_surge import (
        AntiSurgeMarginPolicy, CompressorAntiSurgeGuard,
    )
    from h2physics.adapters.compressor_map import (
        CompressorCommand, CompressorMapEvidence, CompressorMapLine,
        CompressorOperatingMap, MappedCompressor,
    )

    stage, properties, _ = build_stage(**parameters)
    evidence = CompressorMapEvidence("authored-anti-surge-map-envelope",
        "urn:h2physics:authored-anti-surge-map-envelope", "CC0-1.0", "0"*64)
    operating_map = CompressorOperatingMap("authored-compressor-envelope", 300., 1e6, (
        CompressorMapLine(100., .005, .04, 1.5, 2.5, .7, .9),
        CompressorMapLine(200., .005, .04, 1.5, 2.5, .7, .9),
    ), evidence)
    mapped = MappedCompressor(stage, operating_map)
    inlet = properties.state_pt(1e6, 300.)
    accepted = mapped.evaluate(inlet, (CompressorCommand(0., 150., .02),),
                               clock_id="authored-anti-surge-clock")
    rejected = mapped.evaluate(inlet, (CompressorCommand(0., 150., .015),),
                               clock_id="authored-anti-surge-clock")
    policy = AntiSurgeMarginPolicy("fixture-minimum-flow-excess", 0.001,
                                   "fixture declared static protection margin")
    guard = CompressorAntiSurgeGuard(_boundary(), policy)
    accepted_receipt = guard.evaluate(accepted).require_feasible()
    rejected_receipt = guard.evaluate(rejected)
    assert not rejected_receipt.feasible
    try:
        rejected_receipt.require_feasible()
    except ValueError:
        pass
    else:
        raise AssertionError("An insufficient surge-flow margin was accepted")
    accepted_receipt.require_current()
    rejected_receipt.require_current()
    detached = replace(rejected_receipt)
    try:
        _ = detached.feasible
    except ValueError:
        pass
    else:
        raise AssertionError("A detached anti-surge feasibility result was accepted")
    return ValidationOutcome(True, {
        "feasible_trace_points": len(accepted_receipt.points),
        "infeasible_trace_points": len(rejected_receipt.points),
        "infeasible_native_points_retained": sum(not p.admissible for p in rejected_receipt.points),
        "detached_summary_rejected": 1,
    }, ("Static caller boundary and margin policy only; no surge dynamic/controller claim.",))
