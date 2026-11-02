"""Authored finite-stroke valve definition; nothing executes on import."""


def build_model(*, native_target=None, reverse=False):
    from examples.finite_transfer import build_model as build_transfer
    from h2physics.adapters.lh2dt_valve_actuator import (
        FiniteStrokeValve,
        StrokeActuator,
        ValveEffectiveAreaMap,
        ValveMapEvidence,
    )

    transfer = build_transfer(native_target=native_target, reverse=reverse)
    evidence = ValveMapEvidence(
        evidence_id="authored-map-only-not-hardware-qualified",
        source_uri="urn:h2physics:authored-valve-map",
        license_id="Apache-2.0",
        source_sha256="0"*64,
        fluid_basis="Hydrogen",
        qualified_for_prediction=False,
    )
    area_map = ValveEffectiveAreaMap(
        "authored-equal-percentage-like-map",
        (0., .25, .5, .75, 1.),
        (0., .03, .12, .38, 1.),
        evidence,
    )
    actuator = StrokeActuator(
        "authored-finite-stroke",
        opening_rate_fraction_s=2.,
        closing_rate_fraction_s=4.,
        initial_stroke_fraction=0.,
        clock_id="authored-valve-clock",
        evidence_id="authored-rate-not-hardware-qualified",
    )
    model = FiniteStrokeValve(transfer.valves[0], actuator, area_map)
    left = transfer.bridge.native.from_pT(3e6, 300.)
    right = transfer.bridge.native.from_pT(1e6, 300.)
    return model, left, right


def schedule():
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand

    return (
        ValveCommand(0., .5, 1., "open", "operate"),
        ValveCommand(.5, .75, 1., "hold", "hold"),
        ValveCommand(.75, 1., 0., "isolate", "isolate"),
    )


def run_example(*, native_target=None, reverse=False):
    model, left, right = build_model(native_target=native_target, reverse=reverse)
    trace = model.run(left, right, schedule(), (0., .25, .5, .75, 1.),
                      clock_id="authored-valve-clock")
    trace.require_current()
    return model, trace
