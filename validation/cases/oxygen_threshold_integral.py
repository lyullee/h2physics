"""Deferred exact integration of a linearly reconstructed oxygen-threshold deficit."""

import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="oxygen-threshold-deficit-integral",
        profile="oxygen-deficiency",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "positive threshold deficit is integrated analytically on each piecewise-linear output interval",
            "crossing intervals contribute only their below-threshold triangle",
            "units follow mole-fraction or partial-pressure criterion basis",
            "the metric is not reported as human dose or probability",
            "public evaluation requires an owner-issued oxygen criterion result",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.oxygen_threshold_integral import (
        _integrate_positive_threshold_deficit,
        integrate_oxygen_threshold_deficit,
    )

    intervals = _integrate_positive_threshold_deficit(
        (0.0, 1.0, 2.0, 3.0), (0.20, 0.10, 0.20, 0.25), 0.15,
    )
    assert len(intervals) == 3
    assert all(math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-14)
               for value, expected in zip(intervals, (0.0125, 0.0125, 0.0)))
    assert math.isclose(sum(intervals), 0.025, rel_tol=0.0, abs_tol=1e-14)
    rejected = 0
    for invalid in (None, object()):
        try:
            integrate_oxygen_threshold_deficit(invalid)
        except TypeError:
            rejected += 1
        else:
            raise AssertionError("A non-issued criterion input was accepted")
    assert rejected == 2
    return ValidationOutcome(True, {
        "interval_integrals_fraction_seconds": intervals,
        "total_integral_fraction_seconds": sum(intervals),
        "non_owner_inputs_rejected": rejected,
    }, (
        "Exact piecewise-linear metric contract only; no room integration or human-response model is evaluated.",
    ))
