"""Metadata-only Hangang contract for preferred dispersion alarm wiring."""

from inspect import signature

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="preferred-dispersion-receptor-alarm-contract",
        profile="preferred-dispersion",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "caller must declare expected provider family and source domain",
            "receptor frame and clock are bound to the finite source domain",
            "steady receptor field requires constant positive source-bin rates",
            "existing sampled sensor and alarm engines retain native ownership",
            "no plume interpolation, time evolution, or safety credit is introduced",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.preferred_dispersion_alarm import (
        PreferredDispersionAlarmHandoff,
        PreferredDispersionReceptor,
        PreferredDispersionReceptorField,
        bind_preferred_dispersion_receptor_field,
        evaluate_preferred_dispersion_alarm,
    )

    bind_parameters = signature(bind_preferred_dispersion_receptor_field).parameters
    evaluate_parameters = signature(evaluate_preferred_dispersion_alarm).parameters
    required = {"expected_family", "expected_source_domain_id", "clock_id",
                "receptor_mapping_evidence_id", "steady_window_evidence_id"}
    if not required.issubset(bind_parameters):
        raise AssertionError("Caller-declared family/domain or applicability evidence is missing")
    if not {"sensor_config", "alarm_config", "initial_sensor_indication",
            "operating_mode_id", "episode_id"}.issubset(evaluate_parameters):
        raise AssertionError("Existing sampled sensor/alarm context is not explicit")
    return ValidationOutcome(True, {
        "metadata_contract": "passed",
        "public_types": tuple(item.__name__ for item in (
            PreferredDispersionReceptor,
            PreferredDispersionReceptorField,
            PreferredDispersionAlarmHandoff,
        )),
        "declared_family_and_domain_required": True,
        "science_execution_performed": False,
    }, (
        "Metadata-only API contract; no provider field was evaluated",
        "No plume or facility protection qualification is established",
    ))
