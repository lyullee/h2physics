"""Deferred integrity contract for native finite-vessel hydride compression."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-hydride-compressor-trace-issuance",
        profile="hydride-compressor",
        entrypoint=__name__ + ":validate_trace_issuance",
        invariants=(
            "finite hydride and native compressor types are reachable by identity from the lazy storage facade",
            "trace is issued only after completed native coupled integration",
            "direct construction without an integration token is rejected",
            "a consumed compressor trace cannot be cloned and resealed",
            "evidence, initial clock and completed native segment lineage are retained",
            "mutating a retained native integration array invalidates public trace access",
            "event termination matches the terminal accepted sample",
            "all-body mass and energy diagnostics remain within authored synthetic budgets",
        ),
    ),)


def validate_trace_issuance(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from scripts.check_hydride_compressor import make_case, stages
    from importlib import import_module

    from h2physics import storage
    from h2physics.storage.finite_hydride import FiniteHydrideBed
    from h2physics.storage.hydride import HydrideState
    from h2physics.storage.hydride_compressor import (
        HydrideCompressorTrace,
        HydrideThermalCompressor,
    )

    assert storage.FiniteHydrideBed is FiniteHydrideBed
    assert storage.HydrideCompressorTrace is HydrideCompressorTrace
    assert storage.HydrideThermalCompressor is HydrideThermalCompressor
    for name, (module_path, attribute) in storage._LAZY_EXPORTS.items():
        target = import_module(module_path, storage.__name__)
        assert getattr(storage, name) is getattr(target, attribute)

    model = make_case(solid_capacity=50.)
    schedule = stages(model, durations=(50., 40., 60., 50.))
    trace = model.run(
        schedule,
        initial_solid=HydrideState(.01, 300.),
        initial_bed_gas=model.bed.gas.state_pt(2e5, 300.),
        sample_interval_s=2.,
        maximum_step_s=1.,
        relative_tolerance=1e-8,
    )
    assert trace.termination == "schedule_end"
    assert trace.evidence is model.evidence
    assert trace.initial_snapshot.time_s == schedule[0].start_time_s
    assert len(trace.segments) == len(schedule)
    assert all(
        abs(point.total_hydrogen_residual_kg) < 1e-12
        and abs(point.total_energy_residual_j) < 1e-5
        for point in trace.points
    )

    rejected = 0
    for construction in (
        lambda: replace(trace),
        lambda: HydrideCompressorTrace(
            trace.compressor, trace.evidence, trace.initial_snapshot,
            trace.segments, trace.termination, trace.event_time_s, trace.energy_scale_j,
        ),
    ):
        try:
            construction()
        except TypeError:
            rejected += 1
        else:
            raise AssertionError("A compressor trace acquired an unissued integrity baseline")

    native_values = trace.segments[0].native_solution.y
    original_value = float(native_values[0, 0])
    native_values[0, 0] = original_value + 1e-6
    try:
        try:
            trace.require_current()
        except ValueError:
            mutated_native_state_rejected = True
        else:
            raise AssertionError("A mutated native solution remained a current compressor trace")
    finally:
        native_values[0, 0] = original_value
    trace.require_current()

    return ValidationOutcome(
        accepted=True,
        metrics={
            "completed_segments": len(trace.segments),
            "accepted_points": len(trace.points),
            "unissued_constructions_rejected": rejected,
            "native_solution_mutation_rejected": mutated_native_state_rejected,
            "maximum_mass_residual_kg": max(
                abs(point.total_hydrogen_residual_kg) for point in trace.points
            ),
            "maximum_energy_residual_j": max(
                abs(point.total_energy_residual_j) for point in trace.points
            ),
        },
        limitations=(
            "Synthetic hydride/compressor settings and native adapter integrity only.",
            "No alloy, apparatus or cyclic steady-state qualification is implied.",
        ),
    )
