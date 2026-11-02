"""Dormant native FDS cases; import/cases() do not execute geometry or science."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return tuple(
        ValidationCase(
            identifier="obstacle-" + mode,
            profile="obstacle-dispersion",
            entrypoint="validation.cases.obstacle_dispersion:validate_native",
            parameters={"mode": mode},
            invariants=(
                "actual pinned external FDS binary/process and original artifacts",
                "native resolved obstacle bounds/free volume",
                "instantaneous H2 inventories versus mean native source flux",
                "native sensible enthalpy/pressure-work ledger",
                "finite low-speed/source/clock applicability",
                "direct or dataclass-replaced obstacle results cannot fabricate admitted outputs",
                "post-capture changes to native result arrays invalidate the original receipt",
                "post-capture changes to, additions within, or removal from the native artifact tree invalidate the receipt",
            ),
        )
        for mode in ("zero-source", "finite-pulse", "obstacle-pair", "refinement")
    )


def validate_native(*, work_directory, mode):
    import hashlib
    import json
    from pathlib import Path

    import numpy as np

    from examples.obstacle_dispersion import authored_case, selected_engine
    from h2physics.adapters.obstacle_dispersion import (
        ObstacleDispersionError,
        run_obstacle_dispersion,
    )

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    files = (
        "src/h2physics/adapters/obstacle_dispersion.py",
        "examples/obstacle_dispersion.py",
        "validation/cases/obstacle_dispersion.py",
    )
    before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    engine = selected_engine()
    configurations = (
        [(16, True), (16, False)]
        if mode == "obstacle-pair"
        else [(16, True), (32, True)]
        if mode == "refinement"
        else [(16, True)]
    )
    results = []
    try:
        for index, (cells, obstacle_on) in enumerate(configurations):
            case, budgets = authored_case(
                identifier="native_case_" + str(index),
                cells=cells,
                source_on=mode != "zero-source",
                obstacle_on=obstacle_on,
            )
            results.append(
                run_obstacle_dispersion(case, engine, budgets, work_directory=destination)
            )
    except ObstacleDispersionError as failure:
        report = {
            "status": "rejected",
            "cause": str(failure.__cause__),
            "native_artifact_directory": str(failure.directory),
            "actual_process_retained": failure.native_process is not None,
            "audit_failures": [] if failure.result is None else failure.result.failures,
            "begin_sha256": before,
        }
        (destination / "rejected.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        raise
    primary = results[0]
    for result in results:
        result.require_current()
    from dataclasses import replace

    clone_rejected = False
    try:
        replace(primary, _issuer=None)
    except TypeError:
        clone_rejected = True
    if not clone_rejected:
        raise AssertionError("A copied native FDS receipt was issued without its original token")
    original_residuals = primary.residuals
    tampered_residuals = np.array(original_residuals, copy=True)
    tampered_residuals[0, 0] += 1.0
    object.__setattr__(primary, "residuals", tampered_residuals)
    try:
        try:
            primary.require_current()
        except ValueError:
            mutation_rejected = True
        else:
            raise AssertionError("Mutated native FDS result remained current")
    finally:
        object.__setattr__(primary, "residuals", original_residuals)
    primary.require_current()
    artifact_name = next(iter(primary.artifacts.files_sha256))
    artifact_path = primary.artifacts.directory / artifact_name
    original_artifact = artifact_path.read_bytes()
    artifact_tamper_rejected = False
    try:
        artifact_path.write_bytes(original_artifact + b"\n")
        try:
            primary.require_current()
        except ValueError:
            artifact_tamper_rejected = True
        else:
            raise AssertionError("Changed native FDS artifact remained current")
    finally:
        artifact_path.write_bytes(original_artifact)
    if not artifact_tamper_rejected:
        raise AssertionError("Native artifact-byte mutation was not rejected")
    primary.require_current()
    assert all(result.numerically_admitted for result in results)
    assert primary.native_process.returncode == 0 and primary.artifacts.files_sha256
    if mode == "zero-source":
        assert max(abs(primary.hydrogen_mass_kg)) < primary.budgets.mass_kg
    elif mode == "finite-pulse":
        expected = primary.case.source.integrated_mass_kg(primary.case.end_time_s)
        assert (
            abs(primary.hydrogen_mass_kg[-1] - primary.hydrogen_mass_kg[0] - expected)
            < primary.budgets.mass_kg + 1e-3 * expected
        )
    comparison = {}
    if mode in {"obstacle-pair", "refinement"}:
        second = results[1]
        # Explicit comparison-only linear resampling within overlapping native
        # support; no interpolated field is relabeled as actual native output.
        common = np.linspace(
            max(primary.time_s[0], second.time_s[0]), min(primary.time_s[-1], second.time_s[-1]), 81
        )
        a = np.column_stack(
            [
                np.interp(common, primary.time_s, primary.receptor_hydrogen_mole_fraction[:, i])
                for i in range(3)
            ]
        )
        b = np.column_stack(
            [
                np.interp(common, second.time_s, second.receptor_hydrogen_mole_fraction[:, i])
                for i in range(3)
            ]
        )
        difference = float(np.max(abs(a - b)))
        comparison = {
            "receptor_comparison_absolute_mole_fraction": difference,
            "comparison": "linear-only-on-common-native-support",
        }
        if mode == "obstacle-pair":
            assert primary.resolved_obstacles and not second.resolved_obstacles
            assert difference > 1e-10
        else:
            assert difference < 0.01
    after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    assert before == after
    metrics = {
        "actual_native_cases": len(results),
        "direct_or_cloned_receipt_rejected": clone_rejected,
        "post_capture_array_mutation_rejected": mutation_rejected,
        "post_capture_artifact_mutation_rejected": artifact_tamper_rejected,
        "begin_sha256": before,
        "end_sha256": after,
        "binary_sha256": engine.executable_sha256,
        "native_git": primary.native_git_text,
        "maximum_residuals_SI": np.max(abs(primary.residuals), axis=0).tolist(),
        **comparison,
    }
    (destination / "obstacle_dispersion.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    return ValidationOutcome(
        True,
        metrics,
        (
            "Original diagnostic reference; no measured obstacle/H2 validation.",
            "Native FDS low-Mach gas model; no high-pressure source/nozzle/fire-chain acceptance.",
            "Adiabatic walls and the chosen grid/LES require separate qualification.",
        ),
    )
