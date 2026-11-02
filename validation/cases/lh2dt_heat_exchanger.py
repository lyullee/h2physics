"""Deferred finite native exchanger contracts; no calculation at import/discovery."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("hx-boundary-conservation", "validate_conservation", ("both finite fluids/walls respond", "per-side/global mass/U closure")),
        ("hx-boundary-stale", "validate_stale", ("original native rows/trace bound", "method/configuration stale rejection")),
        ("hx-boundary-prefix", "validate_prefix", ("original raw rows and audited prefix", "closed topology admission")),
        ("hx-boundary-limits", "validate_limits", ("zero conductance/isolation", "clock projection rejection/refinement")),
        ("hx-wall-transfer-series", "validate_wall_transfer_series", ("native accepted-clock transfer projection", "source trace freshness and side identity")),
    )
    return tuple(ValidationCase(identifier=name, profile="heat-exchanger-boundaries",
        entrypoint=__name__+":"+function, invariants=invariants) for name, function, invariants in definitions)


def _model(**parameters):
    from examples.lh2dt_heat_exchanger import build_model
    return build_model(**parameters)


def _run(model, *, step=.1, duration=2.):
    return model.run(duration_s=duration, maximum_step_s=step, start_time_s=100., clock_id="authored-HX-clock")


def validate_conservation(*, work_directory, **parameters):
    model, _ = _model(**parameters)
    trace = _run(model)
    trace.require_current()
    assert trace.finite_sides == (model.left, model.right)
    assert trace.native_provenance.package_sha256 == model.native_provenance.package_sha256
    for point in trace.points:
        assert abs(point.global_energy_residual_j) < 1e-5
        assert abs(point.integrated_coupling_residual_j) < 1e-5
        assert abs(sum(side.coupling_heat_into_side_w for side in point.sides.values())) < 1e-9
        for side in point.sides.values():
            assert abs(side.balance.mass_residual_kg) < 1e-12
            assert abs(side.balance.energy_residual_j) < 1e-5
    assert trace.points[-1].sides["left"].fluid.temperature_k < 400.
    assert trace.points[-1].sides["right"].fluid.temperature_k > 250.
    return ValidationOutcome(True, {"accepted_points": len(trace.points),
        "global_energy_residual_j": trace.points[-1].global_energy_residual_j},
        ("Closed lumped thermal pair; no process ports or spatial effectiveness",))


def validate_stale(*, work_directory, **parameters):
    from dataclasses import replace
    model, _ = _model(**parameters)
    trace = _run(model)
    for changed in (replace(trace), replace(trace, requested_end_s=trace.requested_end_s+1)):
        try:
            changed.require_current()
        except ValueError:
            pass
        except RuntimeError:
            pass
        else:
            raise AssertionError("Cloned/relabelled exchanger trace was accepted")
    row = trace.points[-1].native_step
    original_state = row.states[model.equipment_id]
    row.states[model.equipment_id] = replace(original_state, left_integrated_heat_j=1e6)
    try:
        try:
            trace.require_current()
        except RuntimeError:
            pass
        else:
            raise AssertionError("Mutated accepted native row was accepted")
    finally:
        row.states[model.equipment_id] = original_state
    trace.require_current()
    component = model.left.native_component
    original = component.derivative_from_flows
    component.derivative_from_flows = lambda *args, **kw: original(*args, **kw)
    try:
        try:
            trace.require_current()
        except (ValueError, RuntimeError):
            pass
        else:
            raise AssertionError("Rebound native heat method was accepted")
    finally:
        del component.derivative_from_flows
    trace.require_current()
    conductance = component.ambient_UA
    component.ambient_UA = conductance+1.
    try:
        try:
            trace.require_current()
        except RuntimeError:
            pass
        else:
            raise AssertionError("Changed coupling conductance preserved the old trace")
    finally:
        component.ambient_UA = conductance
    trace.require_current()
    return ValidationOutcome(True, {"stale_rejections": 5}, ("Research correspondence guard; no security claim",))


def validate_prefix(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_heat_exchanger import HeatExchangerIntegrationError
    model, native = _model(**parameters)
    def extra_boundary(*, properties):
        network = native["network"].SteadyNetwork(properties=properties)
        network.add_boundary("extra", properties.from_pT(1e5, 300.))
        return network
    changed, _ = _model(network_factory=extra_boundary, **parameters)
    try:
        _run(changed, duration=.2)
    except HeatExchangerIntegrationError as error:
        assert error.cause is error.__cause__
        assert len(error.completed_points) == 1 and error.native_rows
        assert error.native_network is error.native_simulator.network
        assert error.native_components[0] is changed.left.native_component
        assert error.last_trial is not None and error.native_provenance is not None
    else:
        raise AssertionError("Undeclared closed-pair network boundary was accepted")
    assert model is not changed
    return ValidationOutcome(True, {"retained_initial_audited_point": 1},
        ("If native simulate raises before returning rows, only available prefix/last trial can be retained",))


def validate_wall_transfer_series(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    model, _ = _model(**parameters)
    trace = _run(model)
    left = trace.wall_transfer_series("left")
    right = trace.wall_transfer_series("right")
    assert left.require_current() is left and right.require_current() is right
    assert left.clock_id == right.clock_id == trace.clock_id
    assert np.array_equal(left.time_s, trace.time_s)
    assert np.array_equal(right.time_s, trace.time_s)
    assert left.cumulative_heat_into_side_j[0] == 0.
    assert right.cumulative_heat_into_side_j[0] == 0.
    for left_j, right_j, point in zip(
        left.cumulative_heat_into_side_j, right.cumulative_heat_into_side_j,
        trace.points, strict=True,
    ):
        assert np.isclose(left_j+right_j, point.integrated_coupling_residual_j,
                          rtol=1e-12, atol=1e-12)
    for left_w, right_w in zip(left.native_heat_rate_into_side_w,
                               right.native_heat_rate_into_side_w, strict=True):
        assert abs(left_w+right_w) <= model.heat_rate_tolerance_w
    try:
        trace.wall_transfer_series("__unlisted_side__")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown finite exchanger side must be rejected")
    forged = np.array(left.cumulative_heat_into_side_j, copy=True)
    forged[-1] += 1.
    try:
        replace(left, cumulative_heat_into_side_j=forged)
    except ValueError:
        pass
    else:
        raise AssertionError("Altered transfer values must not be resealed from the original trace")
    return ValidationOutcome(True, {
        "accepted_samples": len(left.time_s),
        "left_integrated_heat_into_side_j": float(left.cumulative_heat_into_side_j[-1]),
        "right_integrated_heat_into_side_j": float(right.cumulative_heat_into_side_j[-1]),
    }, ("Native accepted transfer outputs only; no re-integration or independent HX qualification",))


def validate_limits(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_heat_exchanger import HeatExchangerIntegrationError
    zero, _ = _model(conductance=0., **parameters)
    trace = _run(zero)
    trace.require_current()
    for side_id in ("left", "right"):
        first, last = trace.points[0].sides[side_id], trace.points[-1].sides[side_id]
        assert first.inventory == last.inventory
    try:
        zero.run(duration_s=512., maximum_step_s=.1, start_time_s=1e18, clock_id="unresolvable")
    except HeatExchangerIntegrationError as error:
        assert error.native_simulator is None and error.last_trial is None
        assert "clock" in str(error.cause).lower()
    else:
        raise AssertionError("Positive native intervals were lost on an absolute clock")
    coarse_model, _ = _model(**parameters)
    fine_model, _ = _model(**parameters)
    coarse, fine = _run(coarse_model, step=.2), _run(fine_model, step=.1)
    delta = max(abs(coarse.points[-1].sides[name].fluid.temperature_k-
                    fine.points[-1].sides[name].fluid.temperature_k) for name in ("left", "right"))
    assert delta < 1e-3
    return ValidationOutcome(True, {"refinement_temperature_delta_k": delta},
        ("Authored numerical limits, not a measured exchanger/map validation",))
