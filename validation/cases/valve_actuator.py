"""Deferred finite-stroke valve cases; discovery performs no calculation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    definitions = (
        ("valve-actuator-stroke", "validate_stroke", ("finite asymmetric stroke rates", "exact command clock")),
        ("valve-actuator-map", "validate_map", ("admitted CdA-ratio interpolation", "shared nozzle retained")),
        ("valve-actuator-map-inversion", "validate_map_inversion", ("bounded map inversion", "explicit plateau selection")),
        ("valve-actuator-isolation", "validate_isolation", ("finite closing stroke", "zero final source")),
        ("valve-actuator-reverse", "validate_reverse", ("explicit reverse permission", "signed native flow")),
        ("valve-actuator-schedule", "validate_schedule_guards", ("contiguous command support", "sampled boundaries")),
        ("valve-actuator-command-mode", "validate_command_mode", ("runtime mode allowlist", "unknown modes rejected at construction")),
        ("valve-actuator-provenance", "validate_provenance", ("original native results", "stale-owner rejection",
         "direct construction and dataclass replacement cannot forge a successful trace")),
    )
    return tuple(ValidationCase(identifier=name, profile="valve-actuator",
        entrypoint=__name__+":"+function, invariants=invariants)
        for name, function, invariants in definitions)


def validate_command_mode(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand

    invalid = 0
    for mode in ("open", "isolated", "typo", ""):
        try:
            ValveCommand(0., 1., .5, "mode-contract", mode)
        except ValueError:
            invalid += 1
    assert invalid == 4
    valid = tuple(ValveCommand(0., 1., target, f"valid-{mode}", mode)
                  for mode, target in (("operate", .4), ("hold", .4), ("isolate", 0.)))
    assert tuple(command.mode for command in valid) == ("operate", "hold", "isolate")
    return ValidationOutcome(True, {"invalid_modes_rejected": invalid,
                                    "valid_modes_admitted": len(valid)},
                             ("Command labels do not add fail-action or valve-control physics.",))


def _run(*, native_target=None, reverse=False, swap=False):
    from examples.valve_actuator import build_model, schedule
    model, left, right = build_model(native_target=native_target, reverse=reverse)
    if swap:
        left, right = right, left
    trace = model.run(left, right, schedule(), (0., .25, .5, .75, 1.),
                      clock_id="authored-valve-clock")
    return model, trace


def validate_stroke(*, work_directory, **parameters):
    _, trace = _run(**parameters)
    assert tuple(p.stroke_fraction for p in trace.points) == (0., .5, 1., 1., 0.)
    assert tuple(p.command.command_id for p in trace.points) == (
        "open", "open", "hold", "isolate", "isolate")
    return ValidationOutcome(True, {"points": len(trace.points)},
        ("Authored rates only; no measured actuator qualification",))


def validate_map(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_valve_actuator import ValveEffectiveAreaMap

    model, trace = _run(**parameters)
    assert tuple(p.effective_opening_fraction for p in trace.points) == (0., .12, 1., 1., 0.)
    assert all(p.result.nozzle.opening is model.valve.opening for p in trace.points)
    assert all(p.result.native is p.result.native for p in trace.points)
    try:
        ValveEffectiveAreaMap("missing-evidence", (0., 1.), (0., 1.), object())
    except TypeError as error:
        assert "typed source-evidence" in str(error)
    else:
        raise AssertionError("A valve area map without its evidence type was accepted")
    return ValidationOutcome(True, {"maximum_opening": 1.},
        ("CdA ratio is caller data, not a manufacturer valve prediction",
         "map construction requires its typed source-evidence receipt"))


def validate_map_inversion(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.lh2dt_valve_actuator import (
        ValveEffectiveAreaMap, ValveMapEvidence,
    )

    evidence = ValveMapEvidence(
        evidence_id="synthetic-map-contract",
        source_uri="urn:authored-synthetic-map-contract",
        license_id="synthetic-only",
        source_sha256="0"*64,
        fluid_basis="H2",
    )
    mapping = ValveEffectiveAreaMap(
        "synthetic-plateau-map", (0., .25, .5, 1.), (0., .2, .2, 1.), evidence,
    )
    assert mapping.stroke_for_opening(.2) == .25
    assert mapping.stroke_for_opening(.2, selection="maximum") == .5
    stroke = mapping.stroke_for_opening(.6)
    assert abs(mapping.opening_fraction(stroke)-.6) <= 1e-15
    try:
        mapping.stroke_for_opening(1.01)
    except ValueError as error:
        assert "outside" in str(error)
    else:
        raise AssertionError("A target outside the admitted map range was accepted")
    return ValidationOutcome(True, {"plateau_min_stroke": .25,
        "plateau_max_stroke": .5, "interpolated_stroke": stroke},
        ("Synthetic arithmetic only; no measured valve map or prediction is qualified",))


def validate_isolation(*, work_directory, **parameters):
    _, trace = _run(**parameters)
    assert trace.points[-2].mass_flow_kg_s > 0
    assert trace.points[-1].stroke_fraction == 0
    assert trace.points[-1].result.nozzle.regime == "closed"
    return ValidationOutcome(True, {"final_mass_flow_kg_s": trace.points[-1].mass_flow_kg_s},
        ("No seat leakage, backlash or fail-action model",))


def validate_reverse(*, work_directory, **parameters):
    _, blocked = _run(reverse=False, swap=True, **parameters)
    _, allowed = _run(reverse=True, swap=True, **parameters)
    assert all(p.mass_flow_kg_s == 0 for p in blocked.points)
    assert any(p.mass_flow_kg_s < 0 for p in allowed.points)
    return ValidationOutcome(True, {"minimum_reverse_kg_s": min(p.mass_flow_kg_s for p in allowed.points)},
        ("Direction permission is explicit; no check-valve dynamics",))


def validate_schedule_guards(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand
    model, left, right = __import__("examples.valve_actuator", fromlist=["build_model"]).build_model(**parameters)
    try:
        model.run(left, right, (ValveCommand(0., .4, 1., "a"),
            ValveCommand(.5, 1., 0., "b")), (0., .4, .5, 1.), clock_id="authored-valve-clock")
    except ValueError as exc:
        assert "contiguous" in str(exc)
    else:
        raise AssertionError("A schedule gap was accepted")
    return ValidationOutcome(True, {"rejected_gap": 1.},
        ("Command interpolation between unsampled boundaries is intentionally unsupported",))


def validate_provenance(*, work_directory, **parameters):
    from dataclasses import replace

    model, trace = _run(**parameters)
    trace.require_current()
    direct_values = {
        name: getattr(trace, name)
        for name in type(trace).__dataclass_fields__
        if name != "_issuer_token"
    }
    unissued_rejected = 0
    for construct in (
        lambda: type(trace)(**direct_values),
        lambda: replace(trace, output_sha256="0"*64),
    ):
        try:
            construct()
        except TypeError:
            unissued_rejected += 1
    assert unissued_rejected == 2
    original = model.valve.allow_reverse
    model.valve.allow_reverse = not original
    try:
        trace.require_current()
    except ValueError as exc:
        assert "changed" in str(exc)
    else:
        raise AssertionError("A rebound shared-valve owner was accepted")
    finally:
        model.valve.allow_reverse = original
    assert all(p.result.native is not None for p in trace.points)
    return ValidationOutcome(True, {"native_results": len(trace.points),
                                   "unissued_trace_rejections": unissued_rejected},
        ("Content seal does not replay hidden native/property callback state",))
