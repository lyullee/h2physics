"""Metadata-only deferred facility event/native composition acceptance definitions."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; these entrypoints have not run locally.",
    "Authored sensors, reference, latency, geometry and annual probabilities; no facility qualification.",
    "Offline prescribed replay, accepted-sample mass source, fixed declared source state and unresolved field-to-harm mapping.",
    "No automatic frequency, opening, ignition, failure probability or protection reliability credit.",
)


def cases():
    definitions = (
        (
            "facility-native-chain",
            "validate_native_chain",
            (
                "actual registered native alarm",
                "accepted native command/inventory source",
                "original native conditional risk",
                "conditional-risk result revalidates retained source/context/harm/output/receipt",
                "finite-source and native-frequency evidence references resolve in the risk context",
                "replacement output inconsistent with its native receipt is rejected",
                "facility-risk wrapper retains exact source/protected-run/dependence identities",
                "direct wrapper construction and replacement with a different dependence are rejected",
                "dataclasses.replace cannot mint a second facility or native conditional-risk receipt",
            ),
        ),
        (
            "facility-monitor-guards",
            "validate_monitor_guards",
            ("causal usable alarm row", "explicit mode and source clock", "no missing-data trip"),
        ),
        (
            "facility-source-guards",
            "validate_source_guards",
            (
                "accepted mass bins and finite inventory",
                "native/source mutation rejection",
                "accepted-sample outlet enthalpy integral compared with the caller's fixed source-state projection",
                "enthalpy discrepancy retained as a diagnostic rather than misrepresented as source-plane closure",
            ),
        ),
        (
            "finite-source-clock-contract",
            "validate_source_clock_contract",
            (
                "left/right source rates agree with the declared event-edge convention",
                "solver-grid projection preserves all source discontinuities and total mass",
                "finite source window preserves internal jumps and requires explicit truncation meaning",
                "full-tail window cannot relabel the parent's termination meaning",
                "clock mismatch and source-window extrapolation are rejected",
                "nozzle-history conversion requires explicit flow quadrature and representative-state evidence",
                "direct nozzle projection rejects whitespace-only quadrature/state evidence even when source labels match",
                "left-hold, right-hold and trapezoidal nozzle mass bins preserve their selected rules",
                "inventory-limit release termination survives finite-source conversion",
                "nozzle withdrawn/static/kinetic-energy quadratures and representative-state discrepancy are retained",
                "nested native nozzle grids aggregate onto common source bins and expose per-channel sensitivity summaries",
            ),
        ),
        (
            "facility-dependence",
            "validate_dependence",
            ("no renamed physical credit", "no extra reliability credit for resolved path"),
        ),
        (
            "facility-action-failure",
            "validate_action_failure",
            (
                "original action exception",
                "modified target retained without rollback",
                "no invented native run",
            ),
        ),
        (
            "facility-relief-record",
            "validate_relief_record",
            (
                "actual original native latch transition",
                "clock/bracket/threshold provenance",
                "no independent-trace coupling",
            ),
        ),
        (
            "facility-relief-trace-integrity",
            "validate_relief_trace_integrity",
            (
                "immutable aligned accepted-time and cumulative ledgers",
                "mass/energy recomputation from retained native intervals",
                "window versus inventory-floor termination consistency",
            ),
        ),
        (
            "cantera-gas-composition-binding",
            "validate_cantera_gas_composition_binding",
            (
                "mole-basis GasComposition converted to native species mass fractions",
                "declared molar masses checked before provider construction",
                "composition identity and PropertyBasis retained",
                "native composition molar mass and single-state heat-capacity ratio retained",
                "mutated caller composition identity invalidates subsequent provider calls",
                "native frozen-gas state remains owned by Cantera",
                "rejected mismatch leaves supplied native phase unchanged",
            ),
        ),
        (
            "facility-concentration-alarm",
            "validate_concentration_alarm",
            (
                "piecewise-linear input is evaluated through the analytic first-order sensor response",
                "small/large interval-to-time-constant limits remain bounded and monotone",
                "input gaps above the declared response-model limit are rejected",
                "sensor indication retains source, clock, basis, location, mode, episode, origin and model evidence",
                "alarm consumes the issued filtered indication and retains its exact sensor trace",
                "sensor/alarm identity, evidence, mode, episode or origin mismatch is rejected",
                "trip occurs only after the configured consecutive sampled exceedances",
                "reset requires its separate lower threshold and confirmation count",
                "hysteresis-band samples preserve the latched state and cancel pending transitions",
                "confirmation time is the exact sampled decision time; no interpolation is used",
                "source-bound trip evidence is accepted by ScheduledProtection",
                "alarm/voting traces and event evidence reject arbitrary issuer values",
                "dataclass replacement cannot reuse consumed one-use receipt tokens",
                "same-clock 2oo3 voting preserves each original detector evidence and exact active set",
                "voted rise/fall decisions occur on the common sample grid without added delay",
                "misaligned detector clocks are rejected before voting",
                "non-increasing clocks, overlong gaps and nonfinite/negative readings are rejected",
                "the caller threshold evidence and concentration unit remain explicit",
            ),
        ),
    )
    return tuple(
        ValidationCase(
            identifier=name,
            profile="facility-protection",
            entrypoint=__name__ + ":" + function,
            parameters={},
            invariants=invariants,
        )
        for name, function, invariants in definitions
    )


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_concentration_alarm(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.adapters.facility_protection import (
        ProtectionAction,
        ScheduledProtection,
    )
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        ConcentrationAlarmEvidence,
        ConcentrationAlarmVotingEvidence,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm,
        evaluate_concentration_alarm_from_sensor,
        evaluate_concentration_alarm_voting,
        evaluate_first_order_concentration_sensor,
    )
    from h2physics.core import Origin

    sensor = FirstOrderConcentrationSensorConfig(
        "detector-lag", "room-lag", "clock-lag", "dry mole fraction", "mol/mol",
        1.0, 1.0, "sensor-calibration-lag", "response-fit-lag", "first-order-model-v1",
    )
    response = evaluate_first_order_concentration_sensor(
        sensor, time_s=[0., 1., 2.], true_concentration=[0., .02, .02],
        initial_indication=0., source_evidence_id="synthetic-room-history",
        operating_mode_id="normal", episode_id="lag-episode",
        origin=Origin.SYNTHETIC,
    )
    response.require_current()
    expected_at_one = .02 * (1. - 1. / np.e)
    expected_at_two = .02 + (expected_at_one - .02) * np.exp(-1.)
    if (not np.isclose(response.indicated_concentration[1], expected_at_one,
                       rtol=1e-13, atol=1e-15)
            or not np.isclose(response.indicated_concentration[2], expected_at_two,
                              rtol=1e-13, atol=1e-15)):
        raise AssertionError("Piecewise-linear first-order indication differs from its analytic solution")
    slow = replace(sensor, response_time_constant_s=1e12)
    slow_response = evaluate_first_order_concentration_sensor(
        slow, time_s=[0., 1.], true_concentration=[0., .02],
        initial_indication=0., source_evidence_id="synthetic-room-history",
        operating_mode_id="normal", episode_id="lag-episode",
        origin=Origin.SYNTHETIC,
    )
    fast = replace(sensor, response_time_constant_s=1e-9)
    fast_response = evaluate_first_order_concentration_sensor(
        fast, time_s=[0., 1.], true_concentration=[0., .02],
        initial_indication=0., source_evidence_id="synthetic-room-history",
        operating_mode_id="normal", episode_id="lag-episode",
        origin=Origin.SYNTHETIC,
    )
    if (not np.isclose(slow_response.indicated_concentration[-1], 1e-14,
                       rtol=1e-10, atol=1e-25)
            or fast_response.indicated_concentration[-1] != .02):
        raise AssertionError("First-order response lost its small/large time-ratio limit")
    limited = replace(sensor, maximum_input_sample_gap_s=.5)
    try:
        evaluate_first_order_concentration_sensor(
            limited, time_s=[0., 1.], true_concentration=[0., .02],
            initial_indication=0., source_evidence_id="synthetic-room-history",
            operating_mode_id="normal", episode_id="lag-episode",
            origin=Origin.SYNTHETIC,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Sensor model accepted an input interval above its declared maximum")
    lag_alarm = ConcentrationAlarmConfig(
        sensor.sensor_id, sensor.location_id, sensor.clock_id, "normal", "lag-episode",
        sensor.concentration_basis, sensor.concentration_unit, .01, .005, 1, 1, 1.,
        sensor.sensor_evidence_id, "lag-trip-threshold", "lag-alarm-logic",
        Origin.SYNTHETIC,
    )
    lagged_alarm = evaluate_concentration_alarm_from_sensor(lag_alarm, response)
    lagged_alarm.require_current()
    if (lagged_alarm.sensor_response is not response or len(lagged_alarm.transitions) != 1
            or lagged_alarm.transitions[0].confirmation_time_s != 2.):
        raise AssertionError("Alarm did not retain the exact sensor response or lagged trip sample")
    forged_sensor_rejected = False
    try:
        replace(response, _token=object())
    except (TypeError, ValueError):
        forged_sensor_rejected = True
    if not forged_sensor_rejected:
        raise AssertionError("Sensor response issuer token was reusable")
    mismatched = ConcentrationAlarmConfig(
        sensor.sensor_id, sensor.location_id, sensor.clock_id, "normal", "lag-episode",
        sensor.concentration_basis, sensor.concentration_unit, .01, .005, 1, 1, 1.,
        "different-sensor-evidence", "lag-trip-threshold", "lag-alarm-logic",
        Origin.SYNTHETIC,
    )
    try:
        evaluate_concentration_alarm_from_sensor(mismatched, response)
    except ValueError:
        pass
    else:
        raise AssertionError("Alarm accepted mismatched sensor evidence")
    for context_mismatch in (
        replace(lag_alarm, episode_id="different-episode"),
        replace(lag_alarm, origin=Origin.PREDICTED),
    ):
        try:
            evaluate_concentration_alarm_from_sensor(context_mismatch, response)
        except ValueError:
            pass
        else:
            raise AssertionError("Alarm accepted a sensor response from a different episode or origin")

    config = ConcentrationAlarmConfig(
        "detector-A", "room-north", "clock-1", "normal", "episode-1",
        "dry mole fraction", "mol/mol", 0.01, 0.005, 2, 3, 0.5,
        "sensor-calibration-1", "caller-threshold-1", "logic-revision-1",
        Origin.SYNTHETIC,
    )
    trace = evaluate_concentration_alarm(
        config,
        time_s=[0., .2, .4, .6, .8, 1., 1.2, 1.4, 1.6],
        concentration=[.004, .011, .013, .007, .004, .004, .004, .012, .012],
    )
    trace.require_current()
    unforgeable = True
    for candidate in (lambda: replace(trace),
                      lambda: replace(trace, _token=object())):
        try:
            candidate()
        except (TypeError, ValueError):
            pass
        else:
            unforgeable = False
    if not unforgeable:
        raise AssertionError("A reusable alarm/evidence issuer token admitted a forged receipt")
    if len(trace.transitions) != 3:
        raise AssertionError("Trip, reset and second trip should be retained")
    trip, reset, second_trip = trace.transitions
    if (not trip.alarm_active or trip.first_qualifying_index != 1
            or trip.confirmation_index != 2 or trip.confirmation_time_s != .4):
        raise AssertionError("Trip confirmation was not assigned to its exact sampled row")
    if reset.alarm_active or reset.first_qualifying_index != 4 or reset.confirmation_index != 6:
        raise AssertionError("Reset did not use its own consecutive lower-threshold count")
    if not second_trip.alarm_active or not np.array_equal(
        trace.latched_alarm,
        [False, False, True, True, True, True, False, False, True],
    ):
        raise AssertionError("Hysteresis state does not match the configured thresholds")
    evidence = ConcentrationAlarmEvidence.bind(trace, trip)
    evidence.require_current()
    for candidate in (lambda: replace(evidence),
                      lambda: replace(evidence, _token=object())):
        try:
            candidate()
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("A reusable alarm-evidence token admitted a forged receipt")
    action = ProtectionAction(
        "isolate-feed", "declared-protection", "feed", "isolation", "running",
        "isolated", .1, "latency-evidence", "prescribed-counterfactual-replay",
        Origin.SYNTHETIC,
    )
    scheduled = ScheduledProtection(
        evidence, action, target=object(), native_context=object(),
        read_mode=lambda target: "running", apply=lambda at, context: None,
    )
    scheduled.require_current()
    if scheduled.time_s != .5:
        raise AssertionError("Protection action was not scheduled from confirmation plus declared latency")

    detector_b = ConcentrationAlarmConfig(
        "detector-B", "room-south", "clock-1", "normal", "episode-1",
        "dry mole fraction", "mol/mol", 0.01, 0.005, 2, 3, 0.5,
        "sensor-calibration-B", "caller-threshold-B", "logic-revision-B",
        Origin.SYNTHETIC,
    )
    detector_c = ConcentrationAlarmConfig(
        "detector-C", "room-east", "clock-1", "normal", "episode-1",
        "dry mole fraction", "mol/mol", 0.01, 0.005, 2, 3, 0.5,
        "sensor-calibration-C", "caller-threshold-C", "logic-revision-C",
        Origin.SYNTHETIC,
    )
    trace_b = evaluate_concentration_alarm(
        detector_b, time_s=trace.time_s,
        concentration=[.004, .011, .013, .011, .004, .004, .004, .004, .004],
    )
    trace_c = evaluate_concentration_alarm(
        detector_c, time_s=trace.time_s,
        concentration=[.004, .004, .004, .011, .013, .004, .004, .004, .004],
    )
    vote = evaluate_concentration_alarm_voting(
        (trace, trace_b, trace_c), votes_required=2,
        voting_id="authored-2oo3", logic_evidence_id="authored-vote-logic",
    )
    vote.require_current()
    vote_evidence = ConcentrationAlarmVotingEvidence.bind(vote, vote.transitions[0])
    for original in (vote, vote_evidence):
        for candidate in (lambda value=original: replace(value),
                          lambda value=original: replace(value, _token=object())):
            try:
                candidate()
            except (TypeError, ValueError):
                pass
            else:
                raise AssertionError("A reusable vote issuer token admitted a forged receipt")
    if (len(vote.transitions) != 2 or not vote.transitions[0].alarm_active
            or vote.transitions[0].sample_index != 2
            or vote.transitions[0].active_detector_ids != ("detector-A", "detector-B")
            or vote.transitions[1].alarm_active or vote.transitions[1].sample_index != 6):
        raise AssertionError("2oo3 vote must retain same-sample rising and falling decisions")
    voted_evidence = vote_evidence
    voted_evidence.require_current()
    voted_schedule = ScheduledProtection(
        voted_evidence, action, target=object(), native_context=object(),
        read_mode=lambda target: "running", apply=lambda at, context: None,
    )
    if voted_schedule.time_s != .5 or set(voted_evidence.sensor_evidence_ids) != {
        "detector-A", "detector-B", "detector-C",
    }:
        raise AssertionError("Voted protection must retain detector evidence and declared latency")
    invoked_mode = {"value": "running"}
    applied = []
    replay = ScheduledProtection(
        voted_evidence, action, target=invoked_mode, native_context=object(),
        read_mode=lambda target: target["value"],
        apply=lambda at, context: applied.append((at, context)),
    )
    invocation = replay.command.apply(replay.time_s, replay.native_context)
    replay.require_current()
    if (invocation is None or replay.invocation is None or replay.failure is not None
            or replay.invocation.mode_before != "running"
            or replay.invocation.mode_after != "running" or len(applied) != 1):
        raise AssertionError("Callback completion must remain distinct from physical mode transition")
    rejected_alignment = False
    misaligned_trace = evaluate_concentration_alarm(
        detector_b, time_s=trace.time_s + 0.01,
        concentration=[.004, .011, .013, .011, .004, .004, .004, .004, .004],
    )
    try:
        evaluate_concentration_alarm_voting(
            (trace, misaligned_trace), votes_required=1,
            voting_id="bad-grid", logic_evidence_id="authored-vote-logic",
        )
    except ValueError:
        rejected_alignment = True

    rejected_gap = rejected_clock = rejected_missing = False
    for bad_time, bad_value, label in (
        ([0., .6], [.02, .02], "gap"),
        ([0., 0.], [.02, .02], "clock"),
        ([0., .2], [.02, float("nan")], "missing"),
    ):
        try:
            evaluate_concentration_alarm(config, time_s=bad_time, concentration=bad_value)
        except ValueError:
            if label == "gap":
                rejected_gap = True
            elif label == "clock":
                rejected_clock = True
            else:
                rejected_missing = True
    if not all((rejected_gap, rejected_clock, rejected_missing, rejected_alignment)):
        raise AssertionError("Invalid observation or voting alignment was admitted")
    return ValidationOutcome(True, {
        "transitions": len(trace.transitions),
        "trip_confirmation_time_s": trip.confirmation_time_s,
        "reset_confirmation_time_s": reset.confirmation_time_s,
        "protection_command_time_s": scheduled.time_s,
        "voted_transition_count": len(vote.transitions),
        "2oo3_same_clock_protection": True,
        "callback_completion_not_physical_mode_change": True,
        "explicit_threshold_unit": config.concentration_unit,
        "invalid_gaps_clocks_and_samples_rejected": True,
    }, ("Synthetic discrete alarm logic only; no detector physics, setpoint recommendation or safety qualification.",))


def validate_source_clock_contract(*, work_directory, **parameters):
    import numpy as np

    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.release import (
        NozzleDiagnostics,
        NozzleOpening,
        NozzleResult,
        SourceHistory,
        SourceLocation,
    )
    from h2physics.sources import IntervalMassSource

    del work_directory, parameters
    location = SourceLocation(
        "authored-source", "authored-clock", "global-z-up",
        (0.0, 0.0, 0.0), (0.0, 0.0, 1.0),
    )
    state = ThermoState(
        PropertyBasis("Hydrogen", "authored-interface-only", "normal"),
        100_000.0, 300.0, 0.08, 1_250_000.0, 0.0, 0.0, "gas", vapor_mass_fraction=1.0,
    )
    representative_state = ThermoState(
        state.basis, 100_000.0, 300.0, 0.08, 1_300_000.0, 50_000.0, 10.0,
        "gas", vapor_mass_fraction=1.0,
    )
    source = IntervalMassSource(
        location, np.array([0.0, 1.0, 3.0]), np.array([2.0, 6.0]),
        state, Origin.SYNTHETIC, "authored-source-clock-contract", "window_end",
    )
    _require(source.rate_at(0.0, clock_id=location.clock_id) == 2.0,
             "Initial source edge has only a right-sided rate")
    _require(source.rate_at(1.0, clock_id=location.clock_id, side="left") == 2.0,
             "Left limit at rate discontinuity")
    _require(source.rate_at(1.0, clock_id=location.clock_id) == 3.0,
             "Right limit at rate discontinuity")
    _require(source.rate_at(3.0, clock_id=location.clock_id, side="left") == 3.0,
             "Final source edge has only a left-sided rate")
    projected = source.integrate([0.0, 0.5, 3.0], clock_id=location.clock_id)
    _require(np.array_equal(projected.edges_s, [0.0, 0.5, 1.0, 3.0]),
             "Projection retains unsampled source event edges")
    _require(np.allclose(projected.mass_kg, [1.0, 1.0, 6.0], rtol=0.0, atol=1e-14)
             and projected.total_mass_kg == source.total_mass_kg,
             "Projected bins preserve piecewise mass and inventory")
    window = source.window(0.5, 2.0, clock_id=location.clock_id, end_reason="isolation")
    _require(np.array_equal(window.edges_s, [0.5, 1.0, 2.0]),
             "Window retains internal events and requested endpoints")
    _require(np.allclose(window.mass_kg, [1.0, 3.0], rtol=0.0, atol=1e-14),
             "Window mass equals the exact parent-source integral")
    try:
        source.window(0.5, 2.0, clock_id=location.clock_id)
    except ValueError:
        missing_end_reason_rejected = True
    else:
        raise AssertionError("A truncated source window inferred its termination meaning")
    try:
        source.window(0.5, 3.0, clock_id=location.clock_id, end_reason="isolation")
    except ValueError:
        full_tail_relabel_rejected = True
    else:
        raise AssertionError("A full-tail source window relabeled its parent termination")
    try:
        source.rate_at(1.0, clock_id="wrong-clock")
    except ValueError:
        wrong_clock_rejected = True
    else:
        raise AssertionError("A source sample accepted a foreign clock")
    try:
        source.window(-0.1, 1.0, clock_id=location.clock_id, end_reason="isolation")
    except ValueError:
        extrapolation_rejected = True
    else:
        raise AssertionError("A finite source window extrapolated before its support")

    opening = NozzleOpening("authored-opening", 1.0, 0.5, "authored-effective-area")
    diagnostics = NozzleDiagnostics(0, 0, 0.0, 0.0, 0.0)
    flowing_left = NozzleResult(opening, state, 100_000.0, 0.5, state,
        1.0, 2.0, 2.0, "choked", diagnostics)
    flowing_right = NozzleResult(opening, state, 100_000.0, 0.5, state,
        1.0, 4.0, 4.0, "choked", diagnostics)
    closed = NozzleResult(opening, state, 100_000.0, 0.0, None,
        0.0, 0.0, 0.0, "closed", diagnostics)
    history = SourceHistory(location, (0.0, 1.0, 3.0),
                            (flowing_left, flowing_right, closed), "isolation")
    projection = history.interval_mass_projection(
        representative_state=representative_state,
        flow_rule="trapezoid",
        quadrature_evidence_id="authored-piecewise-linear-rate-contract",
        state_projection_evidence_id="authored-constant-state-projection-contract",
    )
    trapezoid = projection.source
    _require(np.allclose(trapezoid.mass_kg, [3.0, 4.0], rtol=0.0, atol=1e-14)
             and trapezoid.end_reason == "isolation",
             "Nozzle quadrature preserves finite interval masses and termination")
    _require(np.allclose(projection.interval_static_enthalpy_j, [3_750_000.0, 5_000_000.0],
                         rtol=0.0, atol=1e-8)
             and np.allclose(projection.interval_kinetic_energy_j, [1.5, 2.0], rtol=0.0, atol=1e-12)
             and np.allclose(projection.nozzle_energy_residual_j, [1.5, 2.0], rtol=0.0, atol=1e-12),
             "Nozzle static, kinetic and total energy ledgers use the selected flow quadrature")
    _require(np.allclose(projection.state_projection_residual_j, [150_000.0, 200_000.0],
                         rtol=0.0, atol=1e-8)
             and projection.require_current() is projection,
             "Representative-state energy mismatch is retained and the receipt remains source-bound")
    from dataclasses import replace
    whitespace_evidence_source = replace(
        projection.source,
        evidence_id=":".join((location.source_id, projection.flow_rule, " ", " ")),
    )
    try:
        replace(
            projection,
            source=whitespace_evidence_source,
            quadrature_evidence_id=" ",
            state_projection_evidence_id=" ",
        )
    except ValueError:
        whitespace_projection_evidence_rejected = True
    else:
        raise AssertionError("Direct nozzle projection accepted whitespace-only evidence IDs")
    midpoint = NozzleResult(opening, state, 100_000.0, 0.5, state,
        1.0, 3.0, 3.0, "choked", diagnostics)
    fine_history = SourceHistory(
        location, (0.0, 1.0, 2.0, 3.0),
        (flowing_left, flowing_right, midpoint, closed), "isolation",
    )
    fine_projection = fine_history.interval_mass_projection(
        representative_state=representative_state,
        flow_rule="trapezoid",
        quadrature_evidence_id="authored-nested-grid-contract",
        state_projection_evidence_id="authored-constant-state-projection-contract",
    )
    refinement = projection.compare_refinement(fine_projection)
    mass_summary = refinement.summary("mass_kg")
    _require(refinement.signed_changes("mass_kg") == (0.0, 1.0)
             and mass_summary.coarse_total == 7.0
             and mass_summary.fine_total == 8.0
             and mass_summary.signed_total_change == 1.0,
             "Nested native grids aggregate fine ledgers and summarize observed mass sensitivity")
    left_hold = history.interval_mass_source(
        representative_state=state,
        flow_rule="left_hold",
        quadrature_evidence_id="authored-left-hold-contract",
        state_projection_evidence_id="authored-constant-state-projection-contract",
    )
    right_hold = history.interval_mass_source(
        representative_state=state,
        flow_rule="right_hold",
        quadrature_evidence_id="authored-right-hold-contract",
        state_projection_evidence_id="authored-constant-state-projection-contract",
    )
    _require(np.allclose(left_hold.mass_kg, [2.0, 8.0], rtol=0.0, atol=1e-14)
             and np.allclose(right_hold.mass_kg, [4.0, 0.0], rtol=0.0, atol=1e-14),
             "Endpoint quadrature modes retain their explicit sample convention")
    limited_history = SourceHistory(
        location, (0.0, 1.0, 3.0), (flowing_left, flowing_right, flowing_right), "inventory_limit",
    )
    limited_source = limited_history.interval_mass_source(
        representative_state=state,
        flow_rule="trapezoid",
        quadrature_evidence_id="authored-inventory-limit-quadrature",
        state_projection_evidence_id="authored-constant-state-projection-contract",
    )
    _require(limited_source.end_reason == "inventory_limit",
             "Inventory-limit termination is preserved through the common finite-source type")
    try:
        history.interval_mass_source(
            representative_state=state,
            flow_rule="trapezoid",
            quadrature_evidence_id="",
            state_projection_evidence_id="authored-state-projection",
        )
    except ValueError:
        missing_quadrature_evidence_rejected = True
    else:
        raise AssertionError("Nozzle mass integration accepted missing quadrature evidence")
    return ValidationOutcome(
        True,
        {
            "source_mass_kg": source.total_mass_kg,
            "projected_edges_s": projected.edges_s.tolist(),
            "window_mass_kg": window.total_mass_kg,
            "missing_end_reason_rejected": missing_end_reason_rejected,
            "full_tail_relabel_rejected": full_tail_relabel_rejected,
            "wrong_clock_rejected": wrong_clock_rejected,
            "extrapolation_rejected": extrapolation_rejected,
            "nozzle_trapezoid_mass_kg": trapezoid.total_mass_kg,
            "nozzle_withdrawal_energy_j": list(projection.interval_withdrawal_energy_j),
            "nozzle_static_enthalpy_j": list(projection.interval_static_enthalpy_j),
            "nozzle_kinetic_energy_j": list(projection.interval_kinetic_energy_j),
            "nozzle_energy_residual_j": list(projection.nozzle_energy_residual_j),
            "representative_state_residual_j": list(projection.state_projection_residual_j),
            "whitespace_projection_evidence_rejected": whitespace_projection_evidence_rejected,
            "refinement_mass_signed_change_kg": list(refinement.signed_changes("mass_kg")),
            "refinement_mass_summary": {
                "coarse_total_kg": mass_summary.coarse_total,
                "fine_total_kg": mass_summary.fine_total,
                "absolute_total_change_kg": mass_summary.absolute_total_change,
                "relative_total_change": mass_summary.relative_total_change,
                "maximum_interval_relative_change": mass_summary.maximum_relative_interval_change,
            },
            "nozzle_left_hold_mass_kg": left_hold.total_mass_kg,
            "nozzle_right_hold_mass_kg": right_hold.total_mass_kg,
            "inventory_limit_termination_preserved": limited_source.end_reason == "inventory_limit",
            "missing_quadrature_evidence_rejected": missing_quadrature_evidence_rejected,
        },
        ("Synthetic interface-contract fixture only; no physical release or model accuracy is tested.",),
    )


def validate_native_chain(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.facility_protection import make_case, risk_inputs
    from h2physics.adapters.conditional_risk import (
        ConditionalRiskError,
        ConditionalRiskNative,
        conditional_risk,
        finite_source_sha256,
    )
    from h2physics.adapters.facility_protection import FacilityRiskResult, evaluate_facility_risk

    case = make_case()
    protected, source = case["protected"], case["source"]
    accepted = protected.accepted[0]
    _require(accepted.invocation is case["plan"].invocation, "Original actuator invocation")
    _require(
        any(t is accepted.native_transition for t in protected.native_run.transitions),
        "Original accepted native transition",
    )
    source.require_current()
    projection = source.energy_projection()
    _require(projection.source_sha256 == finite_source_sha256(source.source),
             "Projection retains finite-source identity")
    _require(projection.component_id == source.component_id
             and len(projection.native_integrals) == len(source.source.mass_kg),
             "Native transmitted enthalpy is integrated once per accepted source bin")
    for native, projected, residual in zip(
        projection.native_transport_enthalpy_j,
        projection.projected_enthalpy_j,
        projection.residual_j,
        strict=True,
    ):
        _require(abs((native-projected)-residual) <= 1e-10+1e-12*max(abs(native), abs(projected)),
                 "Reported residual remains the native-versus-projected interval difference")
    # Isolating the feed does not erase stored line/vaporizer inventories.
    after = source.source.mass_between(
        case["plan"].time_s, source.source.edges_s[-1], clock_id=source.source.location.clock_id
    )
    _require(after > 0.0, "Remaining finite downstream inventory can still supply the source")
    native = ConditionalRiskNative.from_installed()
    direct_native_rejected = False
    try:
        ConditionalRiskNative(
            native.package, native.risk_module, native.contracts, native.api,
            native.version, native.source_sha256, native.native_bindings,
        )
    except TypeError:
        direct_native_rejected = True
    _require(direct_native_rejected,
             "Reviewed conditional-risk owners cannot be fabricated from caller modules")
    try:
        replace(native)
    except TypeError:
        native_clone_rejected = True
    else:
        raise AssertionError("A consumed one-use native-owner issuer admitted a clone")
    request, context, dependence, receptor, harm, evidence = risk_inputs(case, native)
    missing_provenance_rejected = 0
    for missing_id in dict.fromkeys((source.source.evidence_id, *request.frequency.evidence_ids)):
        incomplete_context = context.model_copy(update={
            "evidence": tuple(item for item in context.evidence if item.id != missing_id),
        })
        try:
            conditional_risk(
                native, request, incomplete_context, source=source.source,
                receptor=receptor, harm_bindings=harm, evidence=evidence,
            )
        except ConditionalRiskError as error:
            _require(
                error.stage == "physical-source-and-harm-binding",
                "Missing source/frequency evidence fails before native risk evaluation",
            )
            missing_provenance_rejected += 1
        else:
            raise AssertionError("Unresolved finite-source/frequency provenance was admitted")
    _require(
        missing_provenance_rejected == len(set((source.source.evidence_id, *request.frequency.evidence_ids))),
        "Every finite-source and frequency provenance reference is required",
    )
    result = evaluate_facility_risk(
        native,
        request,
        context,
        finite_source=source,
        protected_run=protected,
        dependence=dependence,
        receptor=receptor,
        harm_bindings=harm,
        evidence=evidence,
    )
    _require(result.require_current() is result, "Facility-risk wrapper remains bound to original owners")
    direct_wrapper_rejected = False
    try:
        FacilityRiskResult(result.native_conditional_result, source, protected, dependence)
    except TypeError:
        direct_wrapper_rejected = True
    _require(direct_wrapper_rejected, "Direct facility-risk wrapper construction is rejected")
    try:
        replace(result)
    except TypeError:
        facility_clone_rejected = True
    else:
        raise AssertionError("A one-use facility-risk issuer admitted a copied receipt")
    foreign_dependence = replace(dependence, conditioning_evidence_id="foreign-conditioning-evidence")
    replacement_rejected = False
    try:
        replace(result, dependence=foreign_dependence)
    except (TypeError, ValueError):
        replacement_rejected = True
    _require(replacement_rejected, "Replacement dependence cannot be attached to the original result")
    actual = result.native_conditional_result
    _require(
        actual.original_request is request and actual.source is source.source,
        "Original native request and finite source",
    )
    _require(
        type(actual.native_output) is native.risk_module.RiskOutput,
        "Actual native aggregation, never host probability math",
    )
    _require(actual.require_current() is actual, "Original conditional-risk result remains bound")
    try:
        replace(actual)
    except TypeError:
        conditional_clone_rejected = True
    else:
        raise AssertionError("A one-use conditional-risk issuer admitted a copied result")
    changed_output = actual.native_output.model_copy(update={
        "annual_harm_frequency_per_year": actual.annual_harm_frequency_per_year + 1.
    })
    try:
        replace(actual, native_output=changed_output)
    except ValueError:
        output_receipt_mismatch_rejected = True
    else:
        raise AssertionError("A conditional-risk output inconsistent with its receipt was admitted")
    return ValidationOutcome(
        True,
        {
            "command_time_s": case["plan"].time_s,
            "native_steps": len(source.run.steps),
            "source_mass_kg": source.source.total_mass_kg,
            "post_feed_isolation_source_kg": after,
            "conditional_native_harm_frequency_per_year": actual.annual_harm_frequency_per_year,
            "result_identity_revalidated": True,
            "native_owner_direct_construction_rejected": direct_native_rejected,
            "native_owner_clone_rejected": native_clone_rejected,
            "missing_source_frequency_provenance_rejected": missing_provenance_rejected,
            "facility_result_clone_rejected": facility_clone_rejected,
            "conditional_result_clone_rejected": conditional_clone_rejected,
            "changed_output_receipt_mismatch_rejected": output_receipt_mismatch_rejected,
        },
        LIMITS,
    )


def validate_monitor_guards(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.facility_protection import make_case, prepare_case
    from h2physics.adapters.facility_protection import (
        AlarmEvidence,
        FacilityProtectionError,
        ProtectedEquipmentRun,
        ProtectionAction,
        ScheduledProtection,
        execute_protected,
    )
    from h2physics.core import Origin

    assembly, owner, evaluation, alarm = prepare_case()
    protected_case = make_case()
    protected = protected_case["protected"]
    sensors = dict(alarm.sensor_evidence_ids)
    rejected = 0
    for operation in (
        lambda: ProtectedEquipmentRun(
            protected.native_run,
            protected_case["assembly"].driver,
            protected.plans,
            protected.accepted,
            protected.mode_definition_id,
            protected.scenario_evidence_id,
        ),
        lambda: replace(protected),
        lambda: AlarmEvidence.bind(
            owner,
            evaluation,
            row_index=0,
            observed_mode_id="running",
            sensor_evidence_ids=sensors,
            decision_evidence_id="invalid-warmup-row",
        ),
        lambda: AlarmEvidence.bind(
            owner,
            evaluation,
            row_index=60,
            observed_mode_id="unknown",
            sensor_evidence_ids=sensors,
            decision_evidence_id="wrong-mode",
        ),
        lambda: replace(alarm, decision_evidence_id="changed-source-evidence").require_current(),
        lambda: ProtectionAction(
            "invalid",
            "mechanism",
            "pump",
            "isolation",
            "running",
            "isolated",
            -0.001,
            "negative-latency",
            "prescribed-counterfactual-replay",
            Origin.SYNTHETIC,
        ),
    ):
        try:
            operation()
        except (ValueError, TypeError):
            rejected += 1
        else:
            raise AssertionError(
                "Missing/unalarmed/wrong-mode/changed-provenance/future action admitted"
            )
    action = ProtectionAction(
        "clock-guard",
        "feed-isolation",
        "pump-assembly",
        "isolation",
        "running",
        "isolated",
        0.003,
        "authored-clock-guard",
        "prescribed-counterfactual-replay",
        Origin.SYNTHETIC,
    )
    plan = ScheduledProtection(
        alarm,
        action,
        target=assembly.pump,
        native_context=assembly.network.native,
        read_mode=lambda target: target.mode_id,
        apply=lambda _t, _g: assembly.pump.set_mode("isolated"),
    )
    try:
        execute_protected(
            assembly.driver,
            (plan,),
            duration_s=0.15,
            time_step_s=0.001,
            start_time_s=0.0,
            clock_id="different-unmapped-clock",
            mode_definition_id="explicit-mode",
            scenario_evidence_id="wrong-clock-negative",
        )
    except FacilityProtectionError as error:
        _require(
            error.native_run is None and plan.invocation is None,
            "Wrong-clock action must fail before native physical execution",
        )
        rejected += 1
    else:
        raise AssertionError("Automatic clock mapping admitted")
    return ValidationOutcome(True, {"monitor_action_admission_rejections": rejected}, LIMITS)


def validate_source_guards(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.facility_protection import make_case
    from h2physics.adapters.conditional_risk import finite_source_sha256
    from h2physics.adapters.facility_protection import FiniteFacilitySource

    case, rejected = make_case(), 0
    source = case["source"]
    changed = replace(source.source, mass_kg=source.source.mass_kg * 1.1 + 1e-6)
    try:
        FiniteFacilitySource.bind(
            source.run,
            changed,
            component_id=source.component_id,
            other_net_boundary_mass_kg=source.other_net_boundary_mass_kg,
            reconciliation_evidence_id=source.reconciliation_evidence_id,
            state_projection_evidence_id=source.state_projection_evidence_id,
            tolerances=source.tolerances,
        )
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed mass bins accepted as original native source")
    source.require_current()
    projection = source.energy_projection()
    _require(
        projection.source_sha256 == finite_source_sha256(source.source),
        "Projection retains finite-source identity",
    )
    _require(
        projection.component_id == source.component_id
        and len(projection.native_integrals) == len(source.source.mass_kg),
        "Native transmitted enthalpy is integrated once per accepted source bin",
    )
    for native, projected, residual in zip(
        projection.native_transport_enthalpy_j,
        projection.projected_enthalpy_j,
        projection.residual_j,
        strict=True,
    ):
        _require(
            abs((native - projected) - residual)
            <= 1e-10 + 1e-12 * max(abs(native), abs(projected)),
            "Reported residual remains the native-versus-projected interval difference",
        )
    values = source.run.steps[-1].native.cumulative_boundary_mass_kg
    key = next(iter(values))
    values[key] += 0.001
    try:
        source.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed original accepted native mass ledger accepted")
    return ValidationOutcome(True, {
        "finite_source_and_native_cache_rejections": rejected,
        "source_enthalpy_projection_intervals": len(projection.native_integrals),
        "source_enthalpy_projection_total_residual_j": projection.total_residual_j,
    }, LIMITS)


def validate_dependence(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.facility_protection import make_case, risk_inputs
    from h2physics.adapters.conditional_risk import ConditionalRiskNative
    from h2physics.adapters.facility_protection import (
        FacilityProtectionError,
        evaluate_facility_risk,
    )

    case, native = make_case(), ConditionalRiskNative.from_installed()
    request, context, dependence, receptor, harm, evidence = risk_inputs(case, native)
    rejected = 0
    mapping = dict(dependence.mechanism_by_factor_id)
    mapping["branch-a:path"] = case["plan"].action.mechanism_id
    try:
        replace(dependence, mechanism_by_factor_id=mapping)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Resolved protection path received an extra probability credit")
    mapping["branch-a:path"] = mapping["branch-a:harm"]
    duplicated = replace(dependence, mechanism_by_factor_id=mapping)
    try:
        evaluate_facility_risk(
            native,
            request,
            context,
            finite_source=case["source"],
            protected_run=case["protected"],
            dependence=duplicated,
            receptor=receptor,
            harm_bindings=harm,
            evidence=evidence,
        )
    except FacilityProtectionError as error:
        _require(
            error.result is None and error.__cause__ is error.original_error,
            "Renamed duplicate credit rejects before native probability calculation",
        )
        rejected += 1
    else:
        raise AssertionError("Renamed mechanism received duplicate probability credit")
    return ValidationOutcome(True, {"explicit_dependence_rejections": rejected}, LIMITS)


def validate_action_failure(*, work_directory, **parameters):
    from examples.facility_protection import make_case
    from h2physics.adapters.facility_protection import FacilityProtectionError

    try:
        make_case(fail_action=True)
    except FacilityProtectionError as error:
        _require(error.native_run is None, "Do not invent a returned native run on command failure")
        plan = error.attempted_plans[0]
        _require(
            plan.failure is error.original_error
            and plan.failure.__cause__ is plan.failure.original_error,
            "Original actual command error chain retained",
        )
        _require(
            plan.target.mode_id == "isolated" and plan.invocation is None,
            "Partly changed actual actuator retained without rollback/success promotion",
        )
        return ValidationOutcome(
            True,
            {"original_command_failure_retained": True, "partly_changed_target_retained": True},
            LIMITS,
        )
    raise AssertionError("Failed command admitted as accepted protection")


def validate_relief_record(*, work_directory, **parameters):
    from examples.facility_protection import relief_case
    from h2physics.adapters.facility_protection import ReliefProtectionRecord

    trace = relief_case()
    event = trace.transitions[0]
    record = ReliefProtectionRecord.bind(
        trace,
        event,
        target_id="authored-PRV",
        mechanism_id="autonomous-native-relief",
        evidence_id="authored-native-relief-transition",
    )
    _require(
        record.transition is event and record.trace is trace, "Actual native transition identity"
    )
    event.native_after.set_pressure_Pa += 1.0
    try:
        record.require_current()
    except ValueError:
        return ValidationOutcome(
            True,
            {"original_native_latch_record": True, "native_threshold_mutation_rejected": True},
            LIMITS,
        )
    raise AssertionError("Changed actual native relief threshold accepted")


def validate_relief_trace_integrity(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from examples.facility_protection import relief_case

    trace = relief_case()
    assert all(not getattr(trace, name).flags.writeable for name in (
        "time_s", "mass_residual_kg", "energy_residual_j", "released_mass_kg",
        "released_enthalpy_j", "external_heat_j",
    ))
    altered = np.array(trace.energy_residual_j, copy=True)
    altered[-1] += 1.0
    try:
        replace(trace, energy_residual_j=altered)
    except ValueError as error:
        assert "energy_residual_j" in str(error)
        return ValidationOutcome(True, {
            "accepted_intervals": len(trace.intervals),
            "tampered_trace_rejected": True,
        }, LIMITS)
    raise AssertionError("A relief trace with a changed energy ledger was accepted")


def validate_cantera_gas_composition_binding(*, work_directory, **parameters):
    import hashlib
    from pathlib import Path

    import cantera as ct
    import numpy as np

    from h2physics import GasComposition
    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties

    del work_directory, parameters
    mechanism_path = Path(ct.__file__).parent / "data" / "gri30.yaml"
    raw = mechanism_path.read_bytes()
    native = ct.Solution(yaml=raw.decode(), name="gri30")
    basis = MechanismBasis(
        "installed-Cantera-gri30-composition-binding",
        hashlib.sha256(raw).hexdigest(),
        "Cantera bundled mechanism data; see installed license notices",
        ("https://cantera.org/3.2/python/thermo.html",),
        300., 2000., 1e4, 2e6,
    )
    names = ("H2", "N2", "O2")
    masses = np.array(
        [native.molecular_weights[native.species_index(name)] / 1000. for name in names]
    )
    composition = GasComposition("facility-feed-gas-v1", names, (0.30, 0.60, 0.10), masses)
    properties = CanteraFrozenGasProperties.from_gas_composition(native, basis, composition)
    state = properties.state_pt(2e5, 800.)
    assert properties.composition_id == composition.composition_id
    assert properties.basis == state.basis
    assert state.phase == "gas"
    assert np.isclose(properties.molar_mass_kg_mol, composition.molar_mass_kg_mol,
                      rtol=2e-8, atol=1e-12)
    assert state.heat_capacity_ratio is not None
    assert np.isclose(state.heat_capacity_ratio, state.cp_j_kg_k / state.cv_j_kg_k,
                      rtol=0., atol=0.)
    if properties.composition_correction is not None:
        assert abs(properties.composition_correction.mass_fraction_change) <= (
            properties.composition_correction.declared_tolerance
        )
        assert properties.composition_correction.corrected_sum == 1.0
    assert np.allclose(
        [properties.mass_fractions[name] for name in names],
        composition.mass_fractions, rtol=2e-15, atol=2e-15,
    )
    properties._composition_id = "tampered-composition-label"
    try:
        properties.state_pt(2e5, 800.)
    except ValueError as error:
        assert "identity changed" in str(error)
        properties._composition_id = composition.composition_id
        identity_tampering_rejected = True
    else:
        raise AssertionError("A provider accepted changed caller composition identity")

    mismatched = GasComposition(
        "wrong-mechanism-mass-v1", names, composition.mole_fractions,
        masses * np.array([1.02, 1.0, 1.0]),
    )
    wrong_native = ct.Solution(yaml=raw.decode(), name="gri30")
    native_state_before_rejection = np.array(wrong_native.state, copy=True)
    try:
        CanteraFrozenGasProperties.from_gas_composition(
            wrong_native, basis, mismatched
        )
    except ValueError as error:
        assert "molar masses" in str(error)
        assert np.array_equal(wrong_native.state, native_state_before_rejection)
        return ValidationOutcome(
            True,
            {"species_count": len(names), "state_pressure_pa": state.pressure_pa,
             "mixture_molar_mass_kg_mol": properties.molar_mass_kg_mol,
             "heat_capacity_ratio": state.heat_capacity_ratio,
             "mass_basis_conversion_retained": True,
             "composition_identity_tampering_rejected": identity_tampering_rejected,
             "molar_mass_mismatch_rejected_before_binding": True,
             "native_phase_unchanged_on_rejection": True},
            ("Native ideal-gas integration only; no real-gas, spin, or measured-mixture qualification.",),
        )
    raise AssertionError("Composition masses inconsistent with native species were admitted")
