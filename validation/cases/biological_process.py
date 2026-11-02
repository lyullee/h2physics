"""Deferred provenance contract for the native ADM1 process result."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="biological-run-owner-receipt",
            profile="biological-process",
            entrypoint="validation.cases.biological_process:validate_run_owner",
            parameters={},
            invariants=(
                "only a completed checked native ADM1 integration issues BiologicalRun",
                "direct construction and dataclass replacement cannot claim native execution",
                "mutated samples, balance, native state, or retained solver histories invalidate the receipt",
                "fixture uses explicitly authored synthetic ADM1 inputs and makes no calibration claim",
            ),
        ),
    )


def validate_run_owner(*, work_directory, **_):
    from h2physics.adapters.biological import (
        BiologicalRun,
        QsdSanNative,
    )
    from scripts.check_biological import make_case

    native = QsdSanNative.from_installed()
    model = make_case(native)
    run = model.run(
        start_time_s=864000.0,
        end_time_s=872640.0,
        sample_count=129,
        max_step_s=900.0,
    )
    run.require_current()
    direct = False
    try:
        BiologicalRun(
            run.evidence, run.points, run.balance, run.native_system, run.native_reactor,
            run.native_model, run.native_components, run.native_solution,
            run.native_initial_state, run.native_versions, run.native_source_hashes,
            run.native_threshold_zeroing_kg_m3_or_kmol_m3, run.energy_balance_available,
            run.hydrogen_identity,
        )
    except ValueError:
        direct = True
    cloned = False
    try:
        replace(run)
    except ValueError:
        cloned = True
    if not direct or not cloned:
        raise AssertionError("BiologicalRun admitted a forged or replaced native receipt")

    original_points = run.points
    try:
        object.__setattr__(run, "points", original_points[:-1])
        try:
            run.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("BiologicalRun remained current after sample mutation")
    finally:
        object.__setattr__(run, "points", original_points)
    run.require_current()
    return ValidationOutcome(
        True,
        {"accepted_points": len(run.points),
         "hydrogen_balance_residual_kg": run.balance.hydrogen_residual_kg,
         "forged_receipt_rejected": direct and cloned},
        ("Synthetic native ADM1 receipt-integrity check; not biological calibration or validation.",),
    )
