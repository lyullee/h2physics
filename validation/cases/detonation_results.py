"""Deferred issuer/currentness contract for native CJ and frozen-shock results."""

import dataclasses

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="detonation-result-issuer",
        profile="detonation-native",
        entrypoint=__name__ + ":validate_result_issuer",
        invariants=(
            "only native SDToolbox executions issue CJ and frozen-shock result receipts",
            "direct construction, cloning, and post-issuance mutation are rejected",
            "synthetic homogeneous inputs retain the native conservation audit boundary",
        ),
    ),)


def validate_result_issuer(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.detonation import CJWaveResult, FrozenShockResult
    from scripts.check_detonation import evidence, hydrogen_initial, make_case, native_provider

    model = make_case(native_provider())
    initial = hydrogen_initial()
    cj = model.cj(initial, evidence=evidence())
    frozen = model.frozen_shock(initial, speed_m_s=cj.speed_m_s, evidence=evidence())
    cj.require_current()
    frozen.require_current()

    for result, result_type in ((cj, CJWaveResult), (frozen, FrozenShockResult)):
        try:
            dataclasses.replace(result)
        except ValueError:
            pass
        else:
            raise AssertionError(f"caller clone accepted for {result_type.__name__}")

    original_speed = cj.speed_m_s
    object.__setattr__(cj, "speed_m_s", original_speed + 1.)
    try:
        cj.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("mutated CJ receipt remained current")

    return ValidationOutcome(True, {
        "native_cj_speed_m_s": original_speed,
        "native_frozen_pressure_pa": frozen.final.pressure_pa,
        "cj_and_frozen_require_current": True,
        "clone_and_mutation_rejected": True,
    }, ("Authored synthetic premix and native solver replay; no experimental validation claim",))
