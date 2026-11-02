"""Deferred accounting contracts for scheduled engine boundary streams."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Integrates only caller-prescribed intake, fuel and exhaust schedules.",
    "No valve, injection, cylinder, chemistry or accepted-step solver coupling is implied.",
    "Synthetic schedules are software contracts, not engine measurements.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-engine-boundary-stream-ledger",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_ledger",
            invariants=("signed-intake-fuel-exhaust-mass", "signed-enthalpy-transfer",
                        "linear-flow-times-linear-enthalpy-integrated-exactly",
                        "common-enthalpy-reference-required", "support-bounds-enforced",
                        "source-schedule-mutation-invalidates-ledger"),
        ),
    )


def validate_ledger(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.combustion.closed_charge_engine import EngineBoundarySchedule
    from h2physics.combustion.engine_boundary_ledger import (
        EngineBoundaryStream,
        integrate_engine_boundary_streams,
    )

    times = np.array([10., 11.])

    def stream(identifier, kind, flow, enthalpy, reference="caller:h0"):
        return EngineBoundaryStream(
            identifier=identifier,
            kind=kind,
            mass_flow=EngineBoundarySchedule(
                "mass_flow", "kg/s", f"caller:{identifier}:flow", 10., times,
                np.array(flow, dtype=float),
            ),
            specific_enthalpy=EngineBoundarySchedule(
                "specific_enthalpy", "J/kg", f"caller:{identifier}:h", 10., times,
                np.array(enthalpy, dtype=float),
            ),
            enthalpy_reference=reference,
        )

    items = (
        stream("intake-1", "intake", [2., 2.], [10., 20.]),
        stream("fuel-1", "fuel", [.5, .5], [100., 200.]),
        stream("exhaust-1", "exhaust", [1., 1.], [5., 5.]),
    )
    ledger = integrate_engine_boundary_streams(items, start_time_s=10., end_time_s=11.)
    assert np.array_equal(ledger.time_s, times)
    assert np.isclose(ledger.mass_into_cylinder_kg, 1.5)
    assert np.isclose(ledger.enthalpy_into_cylinder_j, 100.)
    assert np.isclose(ledger.contributions[0].enthalpy_into_cylinder_j, 30.)
    assert np.isclose(ledger.contributions[1].enthalpy_into_cylinder_j, 75.)
    assert np.isclose(ledger.contributions[2].enthalpy_into_cylinder_j, -5.)
    assert ledger.require_current() is ledger

    rejected = 0
    try:
        integrate_engine_boundary_streams(
            (items[0], replace(items[1], enthalpy_reference="other:h0"), items[2]),
            start_time_s=10., end_time_s=11.,
        )
    except ValueError:
        rejected += 1
    try:
        integrate_engine_boundary_streams(items, start_time_s=9.9, end_time_s=11.)
    except ValueError:
        rejected += 1
    assert rejected == 2

    stale = items[0].mass_flow
    original = stale.values
    object.__setattr__(stale, "values", np.array([3., 3.]))
    try:
        try:
            ledger.require_current()
        except ValueError:
            rejected += 1
    finally:
        object.__setattr__(stale, "values", original)
    assert rejected == 3
    return ValidationOutcome(
        True,
        {"signed_mass_into_cylinder_kg": ledger.mass_into_cylinder_kg,
         "signed_enthalpy_into_cylinder_j": ledger.enthalpy_into_cylinder_j,
         "rejected_bad_reference_bounds_or_mutation": rejected},
        LIMITS,
    )
