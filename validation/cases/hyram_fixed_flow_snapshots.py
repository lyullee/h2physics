"""Deferred contracts for the fixed-flow HyRAM receiver snapshot boundary."""

from dataclasses import dataclass
from types import SimpleNamespace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hyram-finite-source-fixed-flow-snapshots",
            profile="preferred-dispersion",
            entrypoint=__name__ + ":validate_fixed_flow_snapshots",
            invariants=(
                "left-hold interval rates and exact absolute source windows reach the receiver in source order",
                "zero-flow source intervals are preserved and do not invoke the receiver",
                "receiver admitted source-plane H2 rates are compared separately with solver acceptance",
                "a rate mismatch is retained as a rejected diagnostic and is never rescaled",
                "receiver exceptions and their native failure objects remain attached to the exact source interval",
                "the result identifies the injected receiver and states that independent snapshots contain no plume memory",
                "the current stationary HyRAM orifice route cannot be represented as a fixed-flow receiver",
            ),
        ),
    )


def _projection():
    import numpy as np

    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import (
        NozzleDiagnostics, NozzleOpening, NozzleResult, SourceHistory, SourceLocation,
    )

    basis = PropertyBasis("Hydrogen", "fixed-flow-snapshot-fixture", "normal")
    air_basis = PropertyBasis("Air", "fixed-flow-snapshot-fixture")
    ambient = ThermoState(air_basis, 101325., 298.15, 1.2, 300000., 214000., 6800., "gas")
    states = tuple(ThermoState(
        basis, pressure, 300., 1.6, 4.0e6, 2.75e6, 50000., "gas",
    ) for pressure in (2.0e6, 1.8e6, 1.7e6, 1.6e6))
    opening = NozzleOpening.circular(
        "fixture-opening", .01, effective_area_factor=1., area_basis_id="synthetic",
    )
    rates = (.01, .02, 0., 0.)
    samples = tuple(NozzleResult(
        opening=opening,
        upstream_stagnation=state,
        back_pressure_pa=ambient.pressure_pa,
        effective_area_m2=opening.nominal_area_m2,
        exit_state=None,
        velocity_m_s=0. if rate == 0. else 100.,
        mass_flux_kg_m2_s=0. if rate == 0. else rate/opening.nominal_area_m2,
        mass_flow_kg_s=rate,
        regime="closed" if rate == 0. else "back_pressure_limited",
        diagnostics=NozzleDiagnostics(1, 0, 0., 0., 0.),
        model_id="synthetic-fixed-flow-source-contract",
    ) for state, rate in zip(states, rates, strict=True))
    location = SourceLocation(
        "fixture-source", "plant-clock", "global-xz", (0., 0., 0.), (1., 0., 0.),
    )
    history = SourceHistory(location, (5., 15., 25., 35.), samples, "window_end")
    representative = states[0]
    projection = history.interval_mass_projection(
        representative_state=representative,
        flow_rule="left_hold",
        quadrature_evidence_id="synthetic-left-hold",
        state_projection_evidence_id="synthetic-state-map",
    )
    return projection, ambient


def validate_fixed_flow_snapshots(*, work_directory, **parameters):
    from h2physics.adapters.hyram_finite_source_snapshots import (
        HyRAMFixedFlowCondition,
        HyRAMFixedFlowRun,
        HyRAMFiniteSourceSnapshotError,
        run_hyram_finite_source_snapshots,
    )

    del work_directory, parameters
    projection, ambient = _projection()
    condition = HyRAMFixedFlowCondition(
        ambient,
        SimpleNamespace(identity="synthetic-native-atmosphere"),
        "synthetic-atmosphere",
        "synthetic-property-map",
        {"maximum_distance_m": 100.},
    )

    @dataclass
    class Receiver:
        calls: list
        offset_interval: int | None = None

        def run_fixed_flow_snapshot(self, **kwargs):
            self.calls.append(kwargs)
            rate = kwargs["mass_flow_kg_s"]
            admitted = rate*1.01 if len(self.calls)-1 == self.offset_interval else rate
            return HyRAMFixedFlowRun(
                native_result=SimpleNamespace(interval=(kwargs["start_s"], kwargs["end_s"])),
                method_id="synthetic-fixed-flow-receiver/v1",
                requested_mass_flow_kg_s=rate,
                accepted_mass_flow_kg_s=admitted,
                accepted=True,
            )

    receiver = Receiver([])
    series = run_hyram_finite_source_snapshots(
        projection,
        receiver=receiver,
        conditions=(condition, condition, None),
        receiver_identity="synthetic-fixed-flow-receiver/v1",
        source_rate_budget_kg_s=1.e-9,
    )
    assert [call["mass_flow_kg_s"] for call in receiver.calls] == [.01, .02]
    assert [(call["start_s"], call["end_s"]) for call in receiver.calls] == [
        (5., 15.), (15., 25.),
    ]
    assert series.interval_results[2].requested_mass_kg == 0.
    assert series.interval_results[2].run is None
    assert series.all_intervals_accepted
    assert abs(series.requested_source_mass_kg-.3) <= 1e-14
    assert series.source_plane_mass_residual_kg == 0.
    assert not series.plume_memory_included
    assert series.method_id == "independent_quasi_steady_fixed_flow_snapshots"
    native = series.interval_results[0].run.native_result
    original_interval = native.interval
    native.interval = (6., 16.)
    try:
        series.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Mutated native receiver output kept its prior admission")
    finally:
        native.interval = original_interval
    series.require_current()

    mismatched_receiver = Receiver([], offset_interval=0)
    try:
        run_hyram_finite_source_snapshots(
            projection,
            receiver=mismatched_receiver,
            conditions=(condition, condition, None),
            receiver_identity="synthetic-fixed-flow-receiver/v1",
            source_rate_budget_kg_s=1.e-9,
        )
    except HyRAMFiniteSourceSnapshotError as exc:
        assert abs(exc.series.interval_results[0].source_rate_residual_kg_s-.0001) <= 1e-15
        assert not exc.series.interval_results[0].accepted
    else:
        raise AssertionError("A receiver-side flow mismatch was accepted")

    failure_object = SimpleNamespace(id="native-failure-fixture")

    class FailingReceiver:
        def run_fixed_flow_snapshot(self, **kwargs):
            error = RuntimeError("synthetic native receiver failure")
            error.native_result = failure_object
            raise error

    failed = run_hyram_finite_source_snapshots(
        projection,
        receiver=FailingReceiver(),
        conditions=(condition, condition, None),
        receiver_identity="synthetic-failing-receiver/v1",
        source_rate_budget_kg_s=1.e-9,
        require_accepted=False,
    )
    first = failed.interval_results[0]
    assert first.failure is not None and first.native_failure_result is failure_object
    assert (first.interval_index, first.start_s, first.end_s) == (0, 5., 15.)
    assert not failed.all_intervals_accepted

    try:
        run_hyram_finite_source_snapshots(
            projection,
            receiver=object(),
            conditions=(condition, condition, None),
            receiver_identity="native-stationary-hyram",
            source_rate_budget_kg_s=1.e-9,
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Stationary native HyRAM without fixed-flow input was accepted")

    return ValidationOutcome(
        True,
        {
            "source_mass_kg": series.requested_source_mass_kg,
            "positive_snapshot_calls": len(receiver.calls),
            "zero_flow_interval_skipped": True,
            "receiver_flow_mismatch_retained": True,
            "failure_interval": first.interval_index,
        },
        (
            "Synthetic receiver-contract evidence only; no HyRAM binary or transient dispersion ran.",
            "The direct native HyRAM adapter remains incompatible because it computes its own source flow.",
            "Independent snapshots carry no plume memory and do not support continuous-time dose.",
        ),
    )
