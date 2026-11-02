"""Deferred counterflow heat-exchanger cases; discovery executes no model."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Steady one-dimensional cell-centred heat transfer; no transient hold-up or axial conduction.",
    "Pressure profiles and thermodynamic properties are caller-owned; no pressure-drop closure.",
    "Authored constant-cp numerical reference only; no equipment-data qualification.",
)


def cases():
    definitions = (
        ("counterflow-energy", "validate_energy", ("hot/cold/global enthalpy closure",)),
        ("counterflow-refinement", "validate_refinement", ("spatial-cell refinement",)),
        ("counterflow-zero-ua-limit", "validate_zero_ua_limit", ("small-UA limiting response",)),
        ("counterflow-pressure-contract", "validate_pressure_contract", ("caller pressure faces",)),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="counterflow-heat-exchanger",
            entrypoint=__name__ + ":" + entry,
            parameters={},
            invariants=invariants,
        )
        for name, entry, invariants in definitions
    )


def validate_energy(*, work_directory, **parameters):
    from examples.counterflow_heat_exchanger import build

    owner, boundary = build(8)
    result = owner.solve(boundary)
    assert result.hot_heat_loss_w > 0.0
    assert result.cold_heat_gain_w > 0.0
    assert abs(result.global_energy_residual_w) < 1e-6
    assert result.hot_temperature_k[0] > result.hot_temperature_k[-1]
    assert result.cold_temperature_k[0] > result.cold_temperature_k[-1]
    return ValidationOutcome(True, {"duty_w": result.hot_heat_loss_w}, LIMITS)


def validate_refinement(*, work_directory, **parameters):
    from examples.counterflow_heat_exchanger import build

    results = []
    for cells in (8, 16, 32):
        owner, boundary = build(cells)
        results.append(owner.solve(boundary))
    coarse_error = abs(results[0].hot_heat_loss_w / results[-1].hot_heat_loss_w - 1.0)
    fine_error = abs(results[1].hot_heat_loss_w / results[-1].hot_heat_loss_w - 1.0)
    assert fine_error < coarse_error and fine_error < 2e-3
    return ValidationOutcome(True, {"fine_relative_duty_error": fine_error}, LIMITS)


def validate_zero_ua_limit(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.counterflow_heat_exchanger import build

    owner, boundary = build(8)
    tiny = replace(owner.definition, conductance_w_k=(1e-9,) * 8)
    owner = type(owner)(
        tiny,
        hot_state_ph=owner.hot_state_ph,
        cold_state_ph=owner.cold_state_ph,
        domain=owner.domain,
        energy_absolute_tolerance_w=1e-8,
    )
    result = owner.solve(boundary)
    assert 0.0 < result.hot_heat_loss_w < 1e-5
    return ValidationOutcome(True, {"limiting_duty_w": result.hot_heat_loss_w}, LIMITS)


def validate_pressure_contract(*, work_directory, **parameters):
    from dataclasses import replace
    from types import SimpleNamespace

    from examples.counterflow_heat_exchanger import build

    owner, boundary = build(8)
    rejected = 0
    for changed in (
        replace(boundary, hot_pressure_pa_absolute=(2e6,) * 8),
        replace(boundary, cold_pressure_pa_absolute=(1e6,) * 10),
    ):
        try:
            owner.solve(changed)
        except ValueError:
            rejected += 1
    assert rejected == 2
    original = owner.hot_state_ph

    def mismatched_ph(pressure, enthalpy):
        return SimpleNamespace(
            temperature_k=original(pressure, enthalpy).temperature_k,
            pressure_pa=pressure+100., enthalpy_j_kg=enthalpy,
        )

    owner.hot_state_ph = mismatched_ph
    try:
        owner.solve(boundary)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A property closure returning the wrong PH state was admitted")
    return ValidationOutcome(True, {"pressure_profile_rejections": rejected}, LIMITS)

