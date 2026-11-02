"""Deferred finite transfer cases; metadata discovery performs no native calculation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("finite-transfer-two-tanks", "validate_two_tanks", ("both finite native inventories respond", "signed global U/mass closure")),
        ("finite-transfer-isolation", "validate_isolation", ("explicit valve isolation", "remaining finite thermal inventory retained")),
        ("finite-transfer-line", "validate_line", ("actual finite line and both native half-segments", "source/line/receiver inventory closure")),
        ("finite-transfer-reversal", "validate_reversal", ("explicit reverse permission", "signed received mass is not clipped")),
        ("finite-transfer-stop", "validate_stop", ("accepted native termination bracket", "explicit final isolation")),
        ("finite-transfer-prefix", "validate_prefix", ("original domain failure and native attempt retained", "prior accepted prefix preserved")),
        ("finite-transfer-binding", "validate_binding", ("original result/native row ownership", "clock/support/mask/stale guards")),
        ("finite-transfer-refinement", "validate_refinement", ("same declared schedule", "native time-step inventory/pressure refinement")),
        ("finite-transfer-product-boundary-receipt", "validate_product_receipt", (
            "terminal receiver custody boundary must be named with explicit evidence",
            "accepted cumulative receiver mass is differenced into kg and interval-average kg/s",
            "physical-second edges, source identity, LH2 property-reference basis and clock are retained",
            "reverse/net-return intervals cannot be relabeled as product delivery",
            "original finite transfer owner and derived time series are rechecked for freshness",
        )),
    )
    return tuple(ValidationCase(identifier=name, profile="finite-transfer", entrypoint=__name__+":"+function,
        invariants=invariants) for name, function, invariants in definitions)


def _model(**parameters):
    from examples.finite_transfer import build_model
    return build_model(**parameters)


def _run(model, *, step=.05, stages=None, stop=None):
    from examples.finite_transfer import schedule
    return model.run(schedule(model) if stages is None else stages,
        clock_id="authored-transfer-clock", maximum_step_s=step, clock_tolerance_s=1e-10,
        isolate_on_completion=True, stop=stop)


def _balances(trace):
    for point in trace.points:
        assert abs(point.global_mass_residual_kg) < trace.inventory_tolerances.mass_absolute_kg
        assert abs(point.global_energy_residual_j) < trace.inventory_tolerances.energy_absolute_j
        assert abs(point.internal_transport_residual_j) < trace.inventory_tolerances.energy_absolute_j
        for balance in point.balances.values():
            assert not balance.violations(trace.inventory_tolerances)
    for attempt in trace.native_attempts:
        assert attempt.native_simulator is not None and len(attempt.native_rows) == 1
        assert attempt.native_provenance is not None


def validate_two_tanks(*, work_directory, **parameters):
    model = _model(**parameters)
    trace = _run(model)
    trace.require_current()
    _balances(trace)
    final = trace.points[-1]
    assert final.source_withdrawn_kg > 0 and final.receiver_net_received_kg > 0
    assert abs(final.source_withdrawn_kg-final.receiver_net_received_kg) < 1e-8
    source_initial = trace.initial_equipment.node_states[model.source.node_id]
    receiver_initial = trace.initial_equipment.node_states[model.receiver.node_id]
    last_states = final.local_run.steps[-1].equipment.node_states
    assert last_states[model.source.node_id].pressure_pa < source_initial.pressure_pa
    assert last_states[model.receiver.node_id].pressure_pa > receiver_initial.pressure_pa
    assert trace.final_isolated and trace.actual_end_s == trace.requested_end_s
    return ValidationOutcome(True, {"received_kg": final.receiver_net_received_kg,
        "global_energy_residual_j": final.global_energy_residual_j},
        ("Synthetic geometry/opening; no charging protocol or tank qualification",))


def validate_product_receipt(*, work_directory, **parameters):
    del work_directory
    from h2physics.adapters.finite_transfer_product import product_delivery_from_finite_transfer

    model = _model(**parameters)
    trace = _run(model)
    receipt = product_delivery_from_finite_transfer(
        trace, receiver_node_id=model.receiver.node_id,
        product_boundary_evidence_id="authored-receiver-product-custody-boundary")
    assert receipt.require_current() is receipt
    assert receipt.clock_id == trace.clock_id
    assert receipt.rate_series.units == ("kg/s",)
    assert receipt.rate_series.basis_ids == (model.bridge.basis.reference_id,)
    assert receipt.edge_time_s[0] == trace.requested_start_s
    assert receipt.edge_time_s[-1] == trace.actual_end_s
    assert abs(sum(receipt.interval_received_mass_kg)
               - trace.points[-1].receiver_net_received_kg) <= trace.inventory_tolerances.mass_absolute_kg
    try:
        product_delivery_from_finite_transfer(
            trace, receiver_node_id=model.source.node_id,
            product_boundary_evidence_id="wrong-receiver-negative-contract")
    except ValueError:
        wrong_receiver_rejected = True
    else:
        raise AssertionError("A nonreceiver node was accepted as the product custody boundary")
    return ValidationOutcome(True, {
        "intervals": len(receipt.interval_received_mass_kg),
        "delivered_mass_kg": float(sum(receipt.interval_received_mass_kg)),
        "maximum_interval_rate_kg_s": float(max(receipt.interval_average_mass_rate_kg_s)),
        "wrong_receiver_rejected": wrong_receiver_rejected,
    }, ("synthetic transfer and caller-designated custody boundary; no sale, quality or annualization implied",))


def validate_isolation(*, work_directory, **parameters):
    model = _model(**parameters)
    trace = _run(model)
    _balances(trace)
    isolated = [p for p in trace.points if p.stage.mode == "isolated"]
    assert isolated and all(t.mass_flow_kg_s == 0 for p in isolated for t in p.local_run.steps[-1].equipment.transfers)
    for name in (model.source.node_id, model.receiver.node_id):
        assert isolated[0].inventories[name].mass_kg == isolated[-1].inventories[name].mass_kg
        assert isolated[-1].inventories[name].mass_kg > 0
    assert trace.transitions[-1].kind == "caller-completion-isolation"
    return ValidationOutcome(True, {"isolated_steps": len(isolated), "retained_finite_bodies": len(trace.bodies)},
        ("Ideal instantaneous isolation, no leakage/actuator/rundown law",))


def validate_line(*, work_directory, **parameters):
    model = _model(with_line=True, **parameters)
    trace = _run(model, step=.025)
    trace.require_current()
    _balances(trace)
    assert len(trace.bodies) == 3 and len(model.halves) == 2
    assert any(link.component is model.halves[0] for link in trace.native_network.links)
    final = trace.points[-1]
    line_change = final.inventories[model.line.node_id].mass_kg-trace.initial_inventories[model.line.node_id].mass_kg
    assert abs(final.source_withdrawn_kg-final.receiver_net_received_kg-line_change) < 1e-8
    return ValidationOutcome(True, {"line_mass_change_kg": line_change,
        "received_kg": final.receiver_net_received_kg},
        ("Native HEM/transition failures propagate; no automatic alternate friction/flow model",))


def validate_reversal(*, work_directory, **parameters):
    blocked = _model(source_pressure_pa=1e6, receiver_pressure_pa=3e6, reverse=False, **parameters)
    a = _run(blocked)
    assert a.points[-1].receiver_net_received_kg == 0
    reverse = _model(source_pressure_pa=1e6, receiver_pressure_pa=3e6, reverse=True, **parameters)
    b = _run(reverse)
    _balances(b)
    assert b.points[-1].receiver_net_received_kg < 0 and b.points[-1].source_withdrawn_kg < 0
    return ValidationOutcome(True, {"signed_receiver_transfer_kg": b.points[-1].receiver_net_received_kg},
        ("Reverse permission is a caller-declared ideal valve boundary",))


def validate_stop(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_finite_transfer import TransferStop
    model = _model(**parameters)
    initial_mass = model.source.initial_native_state.hydrogen_mass_kg
    trace = _run(model, stop=TransferStop("source-mass-at-most", initial_mass-1e-9,
                                        "authored-sampled-mass-stop"))
    trace.require_current()
    _balances(trace)
    assert trace.termination == "accepted-sample-condition"
    assert trace.stop_time_bracket_s[0] < trace.actual_end_s == trace.stop_time_bracket_s[1]
    assert trace.stop_value <= trace.stop_condition.threshold and trace.final_isolated
    assert trace.actual_end_s < trace.requested_end_s
    return ValidationOutcome(True, {"stop_s": trace.actual_end_s,
        "sampled_mass_overshoot_kg": trace.stop_condition.threshold-trace.stop_value},
        ("Accepted-sample bracket/overshoot; no first-crossing localization or protective-control qualification",))


def validate_prefix(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_finite_transfer import FiniteTransferError, TransferStage
    model = _model(stress_ambient=True, **parameters)
    stages = (TransferStage("stress-domain", 100., 100.2, "isolated", (0.,),
                            "authored-large-ambient-domain-rejection"),)
    try:
        _run(model, step=.1, stages=stages)
    except FiniteTransferError as error:
        assert error.cause is error.__cause__
        assert len(error.completed_points) == 1 and len(error.native_attempts) == 2
        assert error.completed_points[0].time_s == 100.1
        assert error.native_attempts[-1].native_simulator is not None
        assert not error.native_attempts[-1].native_rows
        assert error.last_native_thermo[1] is not None
        assert error.last_accepted_states[model.source.node_id] is error.completed_points[-1].local_run.steps[-1].native.states[model.source.node_id]
    else:
        raise AssertionError("Native finite-wall domain stress was silently repaired")
    return ValidationOutcome(True, {"retained_accepted_prefix": 1},
        ("Authored extreme-temperature rejection input, not a physical fire/heater model",))


def validate_binding(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.lh2dt_finite_transfer import (
        FiniteTransferError,
        TransferAmbient,
        TransferStage,
    )
    model = _model(**parameters)
    trace = _run(model)
    try:
        replace(trace, actual_end_s=trace.actual_end_s+1).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed cached transfer summary acquired original ownership")
    row = trace.points[-1].local_run.steps[-1].native
    original = row.states[model.receiver.node_id]
    row.states[model.receiver.node_id] = replace(original, hydrogen_mass_kg=2*original.hydrogen_mass_kg)
    try:
        try:
            trace.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError("Mutated accepted native inventory was admitted")
    finally:
        row.states[model.receiver.node_id] = original
    trace.require_current()
    wrong = _model(**parameters)
    stages = (TransferStage("outside-history", 103., 104., "isolated", (0.,), "authored"),)
    try:
        _run(wrong, stages=stages)
    except FiniteTransferError as error:
        assert not error.native_attempts and "support" in str(error.cause)
    else:
        raise AssertionError("Ambient history silently extrapolated")
    series = model.source.ambient.series
    try:
        TransferAmbient(replace(series, valid=series.valid & False))
    except ValueError:
        pass
    else:
        raise AssertionError("A masked ambient sample was silently filled")
    try:
        model._project(1e18, .1, 1e-10)
    except ValueError:
        pass
    else:
        raise AssertionError("A positive interval vanished on the absolute clock")
    return ValidationOutcome(True, {"stale_or_support_rejections": 5},
        ("Original owner/state correspondence guards, not a security boundary",))


def validate_refinement(*, work_directory, **parameters):
    coarse, fine = _model(**parameters), _model(**parameters)
    a, b = _run(coarse, step=.05), _run(fine, step=.025)
    _balances(a)
    _balances(b)
    dm = abs(a.points[-1].receiver_net_received_kg-b.points[-1].receiver_net_received_kg)
    pa = a.points[-1].local_run.steps[-1].equipment.node_states[coarse.receiver.node_id].pressure_pa
    pb = b.points[-1].local_run.steps[-1].equipment.node_states[fine.receiver.node_id].pressure_pa
    assert dm < 1e-7 and abs(pa-pb) < 1.
    return ValidationOutcome(True, {"received_mass_refinement_kg": dm, "receiver_pressure_refinement_pa": abs(pa-pb)},
        ("Authored numerical budgets; no independent apparatus or protocol validation",))
