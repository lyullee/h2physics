"""Deferred caller-owned parallel execution contract for independent SLAB slices."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="slabx-caller-executor-snapshots", profile="preferred-dispersion",
        entrypoint=__name__ + ":validate_contract", parameters={},
        invariants=(
            "active independent bins overlap only on a caller-owned executor",
            "zero-mass bins retain empty slots and source-bin order",
            "out-of-order worker completion maps to the original source clock and state",
            "parallel execution requires explicit worker-isolation evidence",
            "parallel failures retain aligned completed outcomes and every failed bin",
            "native width coupling remains caller-owned and is not created by the adapter",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import nullcontext
    from math import log
    from threading import Barrier, Lock
    from time import sleep

    from h2physics.adapters.slabx_lh2 import (
        SLABLH2SnapshotSeriesError,
        run_slabx_lh2_quasi_steady_slices,
    )
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import SourceLocation
    from h2physics.sources import IntervalMassSource

    basis = PropertyBasis("Hydrogen", "synthetic-parallel-slice", "normal")
    gas_constant = 8.314462618 / .00201588
    cp = 14300.0
    state = ThermoState(
        basis, 101325.0, 23.0, 101325.0 / (gas_constant * 23.0),
        cp * 23.0, cp * 23.0 - gas_constant * 23.0,
        cp * log(23.0 / 22.0), "gas", cp_j_kg_k=cp,
        vapor_mass_fraction=1.0,
    )
    source = IntervalMassSource(
        SourceLocation("parallel-source", "plant-clock", "ground-frame", (0., 0., 0.),
                       (0., 0., 1.)),
        (0., 2., 3., 5.), (1., 0., 2.), state, Origin.PREDICTED,
        "parallel-source-evidence", "isolation",
    )

    class Substance:
        mw = .00201588

    class NativePool:
        def __init__(self, *, rate, area, duration, T_source, substance):
            self.rate, self.area, self.duration = rate, area, duration
            self.T_source, self.substance = T_source, substance

        @property
        def T(self):
            return self.T_source

    class Atmosphere:
        p = 101325.0

    class Thermo:
        substance = Substance()

    class Trajectory:
        def __init__(self, rate):
            self.x = [0.0, rate]

    barrier = Barrier(2, timeout=5.0)
    worker_lock = Lock()
    active = 0
    maximum_active = 0

    def runner(native, *args, **kwargs):
        nonlocal active, maximum_active
        with worker_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            barrier.wait()
            if native.rate < 1.0:
                sleep(.03)  # Force the later source bin to finish first.
            return Trajectory(native.rate), native
        finally:
            with worker_lock:
                active -= 1

    def invoke(*, executor=None, parallel_execution_evidence_id=None,
               premise_check=lambda _: {"max": .5, "violated": False}):
        return run_slabx_lh2_quasi_steady_slices(
            source=source, native_pool_factory=NativePool, substance=Substance(),
            area_m2=(1.0, 1.0, 2.0),
            footprint_evidence_id=("first-footprint", "zero-slot", "last-footprint"),
            ambient_pressure_pa=101325.0, atmosphere=Atmosphere(),
            emission_thermo=Thermo(), water_thermo=Thermo(), runner=runner,
            premise_check=premise_check, width_context=lambda _: nullcontext(),
            width_coupling=False, x_max_m=100.0, executor=executor,
            parallel_execution_evidence_id=parallel_execution_evidence_id,
        )

    try:
        invoke(parallel_execution_evidence_id="missing-executor")
    except ValueError:
        pass
    else:
        raise AssertionError("Parallel evidence without a caller executor was accepted")

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = invoke(
            executor=executor,
            parallel_execution_evidence_id="synthetic-thread-safe-native-fixture",
        )
    assert maximum_active == 2
    assert result.parallel_execution_evidence_id == "synthetic-thread-safe-native-fixture"
    assert result.accepted_by_interval == (True, None, True)
    assert tuple(row.interval_index for row in result.source_bin_ledger) == (0, 1, 2)
    assert tuple(row.window_s for row in result.source_bin_ledger) == ((0., 2.), (2., 3.), (3., 5.))
    assert result.interval_runs[1] is None
    assert result.interval_runs[0].boundary.mass_source.edges_s.tolist() == [0., 2.]
    assert result.interval_runs[2].boundary.mass_source.edges_s.tolist() == [3., 5.]
    assert result.interval_runs[0].native.x[-1] == .5
    assert result.interval_runs[2].native.x[-1] == 1.0

    failure_barrier = Barrier(2, timeout=5.0)

    def fail_one(trajectory):
        failure_barrier.wait()
        failed = trajectory.x[-1] == .5
        return {"max": 1.5 if failed else .5, "violated": failed}

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            invoke(executor=executor,
                   parallel_execution_evidence_id="synthetic-thread-safe-native-fixture",
                   premise_check=fail_one)
        except SLABLH2SnapshotSeriesError as error:
            assert error.failed_index == 0
            assert error.result is not None and not error.result.accepted
            assert error.completed_by_interval is not None
            assert len(error.completed_by_interval) == 3
            assert error.completed_by_interval[2] is not None
            assert tuple(index for index, _ in error.failures_by_interval) == (0,)
        else:
            raise AssertionError("A rejected active-bin snapshot was not retained as failure")

    return ValidationOutcome(True, {
        "active_worker_overlap": maximum_active,
        "source_slots": len(result.interval_runs),
        "parallel_evidence_id": result.parallel_execution_evidence_id,
    }, (
        "Synthetic threaded boundary/receipt mechanics only; no SLAB plume solution",
        "Caller evidence does not establish real native-library thread safety",
    ))
