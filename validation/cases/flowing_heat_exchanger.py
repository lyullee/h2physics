"""Deferred flowing heat-exchanger cases; no calculation at discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Closed finite trace point is a hold-up witness, not an open-flow derivative.",
    "No effectiveness, UA, pressure-loss, leakage or spatial-flow model is inferred.",
)


def cases():
    definitions = (
        ("flowing-hx-balanced", "validate_balanced", ("two original process transfers", "side/global enthalpy closure")),
        ("flowing-hx-external", "validate_external", ("explicit external heat", "no inferred utility")),
        ("flowing-hx-pressure", "validate_pressure", ("caller pressure loss", "no extrapolation")),
        ("flowing-hx-witness", "validate_witness", ("finite fluid/wall identity", "original trace point")),
        ("flowing-hx-stale", "validate_stale", ("original result ownership", "mutation rejection")),
        ("flowing-hx-scope", "validate_scope", ("no flowing hold-up derivative claim",)),
    )
    return tuple(ValidationCase(identifier=name, profile="flowing-heat-exchanger",
        entrypoint=__name__+":"+entry, parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)


def _bound(**parameters):
    from examples.flowing_heat_exchanger import bind_example
    from examples.lh2dt_heat_exchanger import build_model

    model, _ = build_model(**parameters)
    trace = model.run(duration_s=0.2, maximum_step_s=0.1,
                      start_time_s=100.0, clock_id="flowing-hx-case")
    owner, sides = bind_example(model, trace)
    return model, trace, owner, sides


def validate_balanced(*, work_directory, **parameters):
    _, trace, owner, sides = _bound(**parameters)
    result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=sides[1])
    assert result.trace_point_index == len(trace.points)-1
    result.require_current()
    assert result.global_energy_residual_w == 0.0
    assert abs(result.total_enthalpy_change_w-result.total_heat_into_streams_w) < 1e-8
    return ValidationOutcome(True, {"side_count": len(result.sides)}, LIMITS)


def validate_external(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.lh2dt_flowing_heat_exchanger import FlowingHeatExchangerSide
    from h2physics.equipment import BoundaryPower

    _, trace, owner, sides = _bound(**parameters)
    right_transfer = replace(sides[1].transfer,
        transmitted=replace(sides[1].transfer.transmitted,
                            enthalpy_j_kg=sides[1].transfer.upstream.enthalpy_j_kg),
        power=BoundaryPower())
    right = FlowingHeatExchangerSide(sides[1].side_id, right_transfer,
        sides[1].pressure_loss_pa, sides[1].pressure_loss_source_id, sides[1].flow_source_id)
    result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=right,
                        external_heat_into_streams_w=100.0)
    assert result.total_heat_into_streams_w == 100.0
    return ValidationOutcome(True, {"external_heat_w": 100.0}, LIMITS)


def validate_pressure(*, work_directory, **parameters):
    from dataclasses import replace

    _, _, _, sides = _bound(**parameters)
    rejected = 0
    for value in (-1.0, sides[0].pressure_loss_pa+1.0):
        try:
            replace(sides[0], pressure_loss_pa=value)
        except ValueError:
            rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"pressure_rejections": rejected}, LIMITS)


def validate_witness(*, work_directory, **parameters):
    _, trace, owner, sides = _bound(**parameters)
    result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=sides[1])
    for side_id, witness in result.witnesses.items():
        snapshot = result.trace_point.sides[side_id]
        assert witness.native_state is snapshot.native_state
        assert witness.fluid_mass_kg == snapshot.inventory.mass_kg
        assert witness.wall_internal_energy_j == snapshot.inventory.solid_internal_energy_j
    return ValidationOutcome(True, {"finite_witnesses": len(result.witnesses)}, LIMITS)


def validate_stale(*, work_directory, **parameters):
    from dataclasses import replace

    _, trace, owner, sides = _bound(**parameters)
    result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=sides[1])
    rejected = 0
    for changed in (replace(result), replace(result, external_heat_into_streams_w=1.0)):
        try:
            changed.require_current()
        except ValueError:
            rejected += 1
    assert rejected == 2
    result.require_current()
    return ValidationOutcome(True, {"stale_rejections": rejected}, LIMITS)


def validate_scope(*, work_directory, **parameters):
    _, trace, owner, sides = _bound(**parameters)
    result = owner.bind(trace, trace_point_index=-1, left=sides[0], right=sides[1])
    assert result.storage_claim == "finite-snapshot-witness-only-no-flowing-hold-up-derivative"
    assert all(witness.total_stored_energy_j for witness in result.witnesses.values())
    return ValidationOutcome(True, {"flowing_storage_derivatives": 0}, LIMITS)
