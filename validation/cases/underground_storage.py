"""Dormant whole-native cavern/ground cases; import/cases() run no model."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = []
    for mode in ("equilibrium", "rock-exchange", "injection-withdrawal", "refinement"):
        invariants = (
            "actual whole native UH2SC Model/solver/cavern/well/GHE",
            "direct HEOS dry-H2/water inventories and phase/partial-pressure closure",
            "all finite rock-node thermal inventory and native boundary heat ledger",
            "selected native independent output series preserves the exact description and accepted clock",
            "UndergroundTrace is issued only after native execution and independent audit; cloning cannot mint a trace",
            "strict failure retention; no native indexing repair or fallback",
        )
        if mode == "injection-withdrawal":
            invariants += (
                "accepted native dry-H2 withdrawal projects to common IntervalMassSource with explicit quadrature/state evidence",
                "signed injection/withdrawal zero crossing is retained as an interval edge",
                "shared source retains absolute operation clock and finite termination reason",
            )
        definitions.append(ValidationCase(
            identifier="underground-" + mode,
            profile="underground-storage",
            entrypoint="validation.cases.underground_storage:validate_native",
            parameters={"mode": mode},
            invariants=invariants,
        ))
    return tuple(definitions)


def validate_native(*, work_directory, mode):
    import copy
    import hashlib
    import json
    from pathlib import Path

    import numpy as np

    from examples.underground_storage import authored_inputs, authored_owner
    from h2physics.adapters.underground_storage import UndergroundStorageError

    destination = Path(work_directory)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    files = (
        "src/h2physics/adapters/underground_storage.py",
        "examples/underground_storage.py",
        "validation/cases/underground_storage.py",
        "src/h2physics/thermo/coolprop.py",
    )
    before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    solver = {"TOL": 1e-9, "LOG_PROGRESS": False, "MAXITER": 100, "USE_RELATIVE_CONVERGENCE": True}
    actual_mode = "rock-exchange" if mode == "refinement" else mode
    traces = []
    try:
        for step, cells in ((2.0, 8), (1.0, 16)) if mode == "refinement" else ((2.0, 8),):
            traces.append(
                authored_owner().run(
                    authored_inputs(mode=actual_mode, step_s=step, rock_cells=cells),
                    solver_options=copy.deepcopy(solver),
                )
            )
    except UndergroundStorageError as failure:
        model = failure.native_model
        if model is not None and model.solutions:
            np.savez(
                destination / "rejected_actual_native_prefix.npz",
                time_s=np.array(tuple(model.solutions)),
                native_states=np.array(tuple(model.solutions.values())),
            )
        rejected = {
            "status": "rejected",
            "cause": str(failure.__cause__),
            "native_object_returned": model is not None,
            "native_time_s": None
            if failure.native_time_s is None
            else float(failure.native_time_s),
            "audited_prefix": len(failure.snapshots),
            "begin_sha256": before,
            "full_audit_failures": [] if failure.trace is None else failure.trace.failures,
        }
        (destination / "rejected.json").write_text(
            json.dumps(rejected, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
        )
        raise
    primary = traces[-1]
    from dataclasses import replace

    try:
        replace(primary)
    except ValueError:
        pass
    else:
        raise AssertionError("UndergroundTrace clone retained native execution authority")
    assert (
        primary.native_model.__class__.__module__ == "uh2sc.model" and primary.numerically_admitted
    )
    assert primary.snapshots[-1].native_time_s == 12.0
    assert all(p.hydrogen_mass_kg > 0 and p.liquid_water_mass_kg > 0 for p in primary.snapshots)
    assert primary.snapshots[-1].time_s == 1012.0
    pressure_series = primary.native_output_series(
        "Total cavern pressure (gasses + water vapor) (Pa)"
    )
    assert pressure_series.require_current() is pressure_series
    assert pressure_series.clock_id == primary.evidence.clock_id
    assert np.array_equal(pressure_series.native_time_s,
                          np.asarray([sample.native_time_s for sample in primary.snapshots]))
    assert np.array_equal(pressure_series.time_s,
                          np.asarray([sample.time_s for sample in primary.snapshots]))
    assert np.array_equal(pressure_series.values,
                          np.asarray([sample.total_pressure_pa_absolute
                                      for sample in primary.snapshots]))
    if mode == "equilibrium":
        assert abs(primary.snapshots[-1].dry_hydrogen.temperature_k - 300.0) < 1e-5
        assert max(np.max(abs(p.rock_temperature_k - 300.0)) for p in primary.snapshots) < 1e-5
    if mode in {"rock-exchange", "refinement"}:
        assert (
            primary.snapshots[-1].fluid_internal_energy_j
            > primary.snapshots[0].fluid_internal_energy_j
        )
        assert primary.boundary_integrals[-1, 3] < 0
    metrics = {
        "samples": len(primary.snapshots),
        "native_source_sha256": dict(primary.native_source_sha256),
        "maximum_residuals_SI": np.max(abs(primary.residuals), axis=0).tolist(),
        "maximum_EOS_relative_defect": max(p.eos_relative_defect for p in primary.snapshots),
        "native_version_labels": primary.native_version_labels,
    }
    if mode == "injection-withdrawal":
        from h2physics.release import SourceLocation

        projection = primary.withdrawal_projection(
            location=SourceLocation(
                "authored-cavern-withdrawal",
                primary.evidence.clock_id,
                "cavern-fixed-frame",
                (0., 0., 0.),
                (0., 0., -1.),
            ),
            representative_state=primary.snapshots[0].dry_hydrogen,
            flow_rule="trapezoid",
            quadrature_evidence_id="authored-native-snapshot-trapezoid",
            state_projection_evidence_id="authored-initial-dry-h2-state-projection",
            end_reason="window_end",
        )
        projection.require_current()
        assert projection.source.total_mass_kg > 0.
        assert np.all(projection.source.mass_kg >= 0.)
        assert projection.source.end_reason == "window_end"
        signed_rates = np.asarray(
            [sample.hydrogen_rate_into_kg_s for sample in primary.snapshots], dtype=float,
        )
        crossing_pairs = [
            (left, right) for left, right in zip(signed_rates[:-1], signed_rates[1:], strict=True)
            if left * right < 0.
        ]
        assert crossing_pairs
        original_times = {sample.time_s for sample in primary.snapshots}
        assert any(edge not in original_times for edge in projection.source.edges_s)
        metrics.update(
            projected_withdrawal_hydrogen_kg=projection.source.total_mass_kg,
            source_interval_count=len(projection.source.mass_kg),
            representative_enthalpy_residual_j=sum(projection.enthalpy_projection_residual_j),
            operation_clock_id=projection.source.location.clock_id,
            signed_flow_crossings=len(crossing_pairs),
        )
    if mode == "refinement":
        coarse, fine = traces
        pressure_error = abs(
            coarse.snapshots[-1].total_pressure_pa_absolute
            / fine.snapshots[-1].total_pressure_pa_absolute
            - 1
        )
        temperature_error = abs(
            coarse.snapshots[-1].dry_hydrogen.temperature_k
            - fine.snapshots[-1].dry_hydrogen.temperature_k
        )
        metrics.update(
            pressure_refinement_relative=pressure_error, temperature_refinement_k=temperature_error
        )
        assert pressure_error < 1e-3 and temperature_error < 0.02
    after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    assert before == after
    metrics.update(begin_sha256=before, end_sha256=after)
    (destination / "underground.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    return ValidationOutcome(
        accepted=True,
        metrics=metrics,
        limitations=(
            "Synthetic inputs and pending native thermal/mass acceptance, no measured cavern validation.",
            "Native suspect ground indexing and fluid caloric convention are not modified.",
            "No salt creep, fracture/leak probability, microbes/geochemistry or saline-brine properties.",
        ),
    )
