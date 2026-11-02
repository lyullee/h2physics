"""Held-current finite reactant event checks using the original stack owner."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="fuel-cell-held-current-positive-time-reserve-event",
        profile="fuel-cell",
        entrypoint=__name__ + ":validate_event",
        invariants=(
            "original-held-current-stack-and-caloric-owner-execute-the-accepted-prefix",
            "H2-O2-and-simultaneous-roots-retain-reserve-and-clock-residuals",
            "prewithdrawal-precedes-full-start-boundary-feeds-without-prorating",
            "idle-and-horizon-complete-remain-distinct-from-reserve-events",
            "initial-boundary-limit-and-negative-inputs-reject-without-fake-time",
            "requested-tail-is-retained-and-native-trace-event-mutation-rejects",
        ),
    ),)


def validate_event(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import isclose

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.fuel_cell_inventory_event import run_fuel_cell_until_reserve
    from h2physics.constants import FARADAY_C_MOL
    from h2physics.core import Origin
    from h2physics.thermochemical import ThermochemicalFeed

    owner, original, commands = synthetic_problem()
    command = replace(commands[0], end_s=1000.)
    rate = command.current_density_a_m2*owner.stack.geometry.active_area_m2
    rate = rate*owner.stack.geometry.series_cells/(2*FARADAY_C_MOL)

    def inventory(h2, o2):
        return replace(original, amounts_mol={"H2": h2, "O2": o2, "H2O": .001})

    def run(initial, schedule=(command,), h=.0001, o=.00005):
        return run_fuel_cell_until_reserve(owner, initial, schedule,
            hydrogen_reserve_mol=h, oxygen_reserve_mol=o)

    hydrogen = run(inventory(.001, .01))
    assert hydrogen.require_current() is hydrogen
    assert hydrogen.status == "reserve_event" and hydrogen.limiting_reactants == ("H2",)
    assert isclose(hydrogen.stop_time_s, (.001-.0001)/rate, rel_tol=1e-13)
    assert abs(hydrogen.trace.final.amounts_mol["H2"]-.0001) < 1e-10
    endpoint = run(inventory(.001, .01), (replace(command, end_s=hydrogen.stop_time_s),))
    assert endpoint.status == "reserve_event" and endpoint.stop_time_s == hydrogen.stop_time_s
    oxygen = run(inventory(.01, .0003))
    assert oxygen.limiting_reactants == ("O2",)
    assert isclose(oxygen.stop_time_s, 2*(.0003-.00005)/rate, rel_tol=1e-13)
    tied = run(inventory(.001, .0005))
    assert tied.limiting_reactants == ("H2", "O2")
    zero_reserve = run(inventory(.001, .01), h=0., o=0.)
    assert zero_reserve.status == "reserve_event"
    assert abs(zero_reserve.trace.final.amounts_mol["H2"]) <= 1e-10

    idle = replace(command, identifier="idle", end_s=3., current_density_a_m2=0.)
    demand = replace(command, identifier="demand", start_s=3.)
    after_idle = run(inventory(.001, .01), (idle, demand))
    assert after_idle.executed_commands[0] is idle
    assert isclose(after_idle.stop_time_s, hydrogen.stop_time_s+3., rel_tol=1e-13)
    complete = run(inventory(.01, .01), (replace(command, end_s=1.),))
    assert complete.status == "horizon_complete" and complete.event_step_index is None
    assert complete.event_time_bracket_s is None

    packet = ThermochemicalFeed(inventory(.001, 0.), "full-start-H2-packet", Origin.SYNTHETIC)
    fed_command = replace(command, feeds=(packet,),
        feed_ports={packet.source_id: owner.boundary.hydrogen_inlet_id},
        pre_withdrawal_mol={"H2": .0005})
    fed = run(inventory(.001, .01), (fed_command,))
    assert isclose(fed.stop_time_s, (.001-.0005+.001-.0001)/rate, rel_tol=1e-13)
    assert fed.executed_commands[0].feeds[0] is packet
    assert fed.trace.steps[0].kernel_trace.feed_mol[owner.kernel.names.index("H2")] == .001
    tail = replace(command, identifier="unused-tail", start_s=1000., end_s=2000.)
    prefix = run(inventory(.001, .01), (command, tail))
    assert prefix.requested_commands[-1] is tail and len(prefix.executed_commands) == 1
    assert prefix.trace.steps[0].command.end_s < command.end_s
    assert command.end_s == 1000.

    # Genuine owner-issued sources bind only to executed packets; a source for
    # an unexecuted tail remains retained in the request and is not consumed.
    donor_command = replace(command, identifier="donor", end_s=1.,
        current_density_a_m2=0., pre_withdrawal_mol={"H2": .001})
    donor_trace = owner.run(inventory(.02, .02), (donor_command,))
    donor = owner.withdrawal(donor_trace, 0, boundary_id=owner.boundary.product_outlet_id,
        frame_id=owner.boundary.frame_id, evidence_id="actual-first-packet")
    future_trace = owner.run(inventory(.02, .02),
        (replace(donor_command, identifier="future-donor", start_s=1000., end_s=1001.),))
    future = owner.withdrawal(future_trace, 0, boundary_id=owner.boundary.product_outlet_id,
        frame_id=owner.boundary.frame_id, evidence_id="actual-future-packet")
    bound_packet = ThermochemicalFeed(replace(original, amounts_mol=dict(donor.amounts_mol)),
        "bound-now", owner.evidence.origin)
    future_packet = ThermochemicalFeed(replace(original, amounts_mol=dict(future.amounts_mol)),
        "bound-future", owner.evidence.origin)
    bound_command = replace(command, feeds=(bound_packet,),
        feed_ports={bound_packet.source_id: owner.boundary.hydrogen_inlet_id})
    bound_tail = replace(tail, feeds=(future_packet,),
        feed_ports={future_packet.source_id: owner.boundary.hydrogen_inlet_id})
    bound = run_fuel_cell_until_reserve(owner, inventory(.001, .01), (bound_command, bound_tail),
        hydrogen_reserve_mol=.0001, oxygen_reserve_mol=.00005,
        feed_bindings={bound_packet.source_id: donor, future_packet.source_id: future})
    assert len(bound.requested_feed_bindings) == 2
    assert bound.trace.feed_bindings == ((bound_packet.source_id, donor),)
    assert bound.executed_commands[0].feeds[0] is bound_packet
    assert bound.require_current() is bound

    rejected = 0
    for operation in (
        lambda: run(inventory(.0001, .01)),
        lambda: run(inventory(.001, .01), h=-.001),
        lambda: run(inventory(.001, .01), (replace(command, pre_withdrawal_mol={"H2": .002},
            feeds=(packet,), feed_ports={packet.source_id: owner.boundary.hydrogen_inlet_id}),)),
        lambda: run(inventory(.001, .01), (replace(command, clock_id="foreign"),)),
        lambda: run(inventory(.001, .01), (command, replace(tail, start_s=1001.))),
        lambda: replace(hydrogen),
        lambda: run_fuel_cell_until_reserve(owner, inventory(.001, .01), (bound_command,),
            hydrogen_reserve_mol=.0001, oxygen_reserve_mol=.00005,
            feed_bindings={bound_packet.source_id: object()}),
    ):
        try:
            operation()
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError("Invalid event boundary/request or receipt reconstruction was admitted")
    previous = hydrogen.stop_time_s
    object.__setattr__(hydrogen, "stop_time_s", previous+1.)
    try:
        hydrogen.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed event time retained native receipt admission")
    finally:
        object.__setattr__(hydrogen, "stop_time_s", previous)
    assert hydrogen.require_current() is hydrogen
    return ValidationOutcome(True, {
        "h2_event_time_s": hydrogen.stop_time_s,
        "o2_event_time_s": oxygen.stop_time_s,
        "fed_event_time_s": fed.stop_time_s,
        "zero_reserve_residual_mol": zero_reserve.trace.final.amounts_mol["H2"],
        "mass_residual_kg": hydrogen.trace.mass_residual_kg,
        "energy_residual_j": hydrogen.trace.energy_residual_j,
        "invalid_requests_and_mutations_rejected": rejected,
        "retained_requested_source_bindings": len(bound.requested_feed_bindings),
        "consumed_prefix_source_bindings": len(bound.trace.feed_bindings),
    }, (
        "Piecewise held current/temperature with complete instantaneous boundary packets",
        "At/below-reserve start boundaries reject; no zero-time physical ledger is invented",
        "Reuses finite owner accounting; not native dynamic/transport event localization",
        "Authored electrical inputs and numerical checks; no measured device validation",
    ))
