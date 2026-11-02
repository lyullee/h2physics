"""Deferred regression contract for finite-source provenance reconstruction."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="oxygen-source-digest-init-fields",
            profile="oxygen-deficiency",
            entrypoint=__name__ + ":validate_contract",
            invariants=(
                "source digest reconstruction excludes dataclass init=False bookkeeping fields",
                "digest revalidation preserves the original finite-source integrity contract",
            ),
        ),
        ValidationCase(
            identifier="oxygen-room-result-issuer",
            profile="oxygen-deficiency",
            entrypoint=__name__ + ":validate_result_issuer",
            invariants=(
                "only a completed CanteraOxygenRoom run can issue an oxygen-result binding",
                "caller construction cannot seal a self-consistent fabricated result around native traces",
                "binding construction without the one-use owner token is rejected",
                "only the oxygen-criterion evaluator can issue a deficit-screen summary",
                "direct and arbitrary-token criterion-result construction is rejected",
                "post-issuance criterion-result edits invalidate its retained screen decision",
            ),
        ),
        ValidationCase(
            identifier="oxygen-criterion-exact-sample-window",
            profile="oxygen-deficiency",
            entrypoint=__name__ + ":validate_exact_window",
            invariants=(
                "criterion reporting windows select ordered exact native output samples",
                "no window edge is interpolated or extrapolated outside the output grid",
                "invalid clocks, non-sample endpoints and reversed windows are rejected",
            ),
        ),
    )


def validate_exact_window(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.oxygen_deficiency import _resolve_exact_output_window

    times = np.array([0.0, 0.25, 1.0, 2.0, 5.0])
    assert _resolve_exact_output_window(times, None) == (0, 4)
    assert _resolve_exact_output_window(times, (0.25, 2.0)) == (1, 3)
    rejected = 0
    for invalid in ((0.3, 2.0), (-1.0, 2.0), (1.0, 1.0), (2.0, 1.0), (0.0, 6.0)):
        try:
            _resolve_exact_output_window(times, invalid)
        except ValueError:
            rejected += 1
    assert rejected == 5
    return ValidationOutcome(
        True,
        {"selected_inclusive_indices": (1, 3), "invalid_windows_rejected": rejected},
        ("Window-index admission only; no Cantera integration or physiological model executed",),
    )


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.oxygen_deficiency import _source_digest
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import SourceLocation
    from h2physics.sources import IntervalMassSource

    basis = PropertyBasis("hydrogen", "oxygen-source-digest-contract", "normal")
    state = ThermoState(basis, 101325., 25., .08, 450000., 320000., 12000., "gas")
    location = SourceLocation("oxygen-digest", "digest-clock", "global-xz",
                              (0., 0., 0.), (1., 0., 0.))
    source = IntervalMassSource(location, np.array([0., 1.]), np.array([.1]), state,
                                Origin.SYNTHETIC, "authored-digest-fixture", "isolation")
    digest = _source_digest(source)
    assert len(digest) == 64
    return ValidationOutcome(True, {"source_sha256": digest},
                             ("Source digest contract only; no oxygen-volume integration executed",))


def validate_result_issuer(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.oxygen_deficiency import (
        OxygenCriterionResult,
        _OxygenResultBinding,
    )

    try:
        _OxygenResultBinding("0" * 64, (), ())
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-created binding was accepted as a completed room run")

    values = (None, None, np.array([True]), 0.0, 1.0, (),
              "linear_between_native_output_samples")
    for token in (None, object()):
        try:
            OxygenCriterionResult(*values, _issuer_token=token)
        except ValueError:
            pass
        else:
            raise AssertionError("A caller-created oxygen criterion result was accepted")

    return ValidationOutcome(
        True,
        {"forged_room_binding_rejected": True, "forged_criterion_result_rejected": True},
        ("Synthetic issuer-boundary checks only; no Cantera integration executed",),
    )
