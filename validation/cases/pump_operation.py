"""Deferred Nurion definitions for finite-speed native pump operation."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Implemented_unverified; no local model, example or case execution.",
    "Native LH2DT remains the pump/network/property owner.",
    "Authored curve data does not qualify a manufacturer pump.",
)


def cases():
    definitions = (
        ("pump-finite-ramp", "validate_finite_ramp", (
            "finite asymmetric speed ramp", "explicit clock",
            "command target changes only after its exact sampled start time",
        )),
        ("pump-map-admission", "validate_map_admission", ("bounded normalized map", "native result retained")),
        ("pump-capacity-rejection", "validate_capacity_rejection", ("no curve extrapolation", "no fallback")),
        ("pump-npsh-rejection", "validate_npsh_rejection", ("native NPSH margin", "inadmissible point retained")),
        ("pump-evidence-gate", "validate_evidence_gate", ("prediction qualification explicit",)),
        ("pump-schedule-guard", "validate_schedule_guard", ("contiguous intervals", "exact boundary samples")),
        ("pump-command-mode", "validate_command_mode", ("runtime mode allowlist", "unknown modes rejected at construction")),
        ("pump-original-result", "validate_original_result", ("native identity", "stale owner rejection",
         "direct construction and dataclass replacement cannot forge a successful trace")),
        ("pump-operation-shaft-connection-boundary", "validate_process_boundary", (
            "accepted native flow/shaft power/outlet enthalpy become typed connection records",
            "receiver absolute pressure and physical sample clock are retained per point",
            "LH2DT property provider identity and spin/reference basis are exact",
            "mutated native pump result and foreign provider owner are rejected",
            "shaft input is not relabeled as electricity, heat or motor efficiency",
        )),
    )
    return tuple(ValidationCase(identifier=name, profile="pump-operation",
        entrypoint=__name__+":"+entry, parameters={}, invariants=invariants)
        for name, entry, invariants in definitions)


def _fixture(*, npsh_available=5.0, native_valid=True):
    from dataclasses import dataclass
    from types import SimpleNamespace

    from h2physics.adapters.lh2dt_pump_operation import (
        FiniteSpeedPump,
        NormalizedPumpMap,
        PumpMapEvidence,
        PumpSpeedActuator,
        PumpSpeedCommand,
    )

    class Pump:
        def __init__(self):
            self.properties = SimpleNamespace(fluid="ParaHydrogen")
            self.reference_speed_rpm = 3000.0
            self.speed_rpm = 1500.0

        def evaluate(self, left, right):
            speed = self.speed_rpm/self.reference_speed_rpm
            rate = 0.004*speed
            return SimpleNamespace(mass_flow_kg_s=rate, npsh_required_m=0.5*speed**2,
                npsh_available_m=npsh_available,
                operating_point_physical_valid=native_valid,
                outlet_specific_enthalpy_J_kg=4e6, shaft_power_W=100.0,
                momentum_residual_Pa=0.0)

    pump = Pump()

    @dataclass
    class State:
        pressure_Pa: float
        density_kg_m3: float = 70.0

    class DynamicRight:
        density_kg_m3 = 70.0

        def __init__(self, native):
            self.native = native
            self.scale = 1.0

        @property
        def pressure_Pa(self):
            speed = self.native.speed_rpm/self.native.reference_speed_rpm
            return 100000.0 + self.scale*450000.0*speed**2

    evidence = PumpMapEvidence("authored", "https://example.invalid/map", "fixture-only",
        "0"*64, "ParaHydrogen", qualified_for_prediction=False)
    pump_map = NormalizedPumpMap("map", 3000.0, 0.008, 600000.0, 0.5,
        (0.0, 0.5, 1.0), (1.0, 0.75, 0.0), (0.7, 0.7, 0.7),
        (1.0, 1.0, 1.0), evidence, relative_admission_tolerance=1e-9)
    actuator = PumpSpeedActuator("drive", "clock", 0.5, 0.5, 1.0, "fixture")
    commands = (PumpSpeedCommand("ramp", 0.0, 1.0, 1.0),
                PumpSpeedCommand("hold", 1.0, 2.0, 1.0, "hold"))
    return FiniteSpeedPump(pump, actuator, pump_map), State(100000.0), DynamicRight(pump), commands


def validate_finite_ramp(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_pump_operation import PumpSpeedCommand

    model, left, right, commands = _fixture()
    trace = model.run(left, right, commands, (0.0, 0.5, 1.0, 2.0), clock_id="clock")
    speeds = tuple(p.speed_fraction for p in trace.points)
    assert speeds == (0.5, 0.75, 1.0, 1.0)
    boundary_commands = (
        PumpSpeedCommand("ramp-up", 0.0, 1.0, 1.0),
        PumpSpeedCommand("ramp-down", 1.0, 2.0, 0.5),
    )
    boundary_trace = model.run(
        left, right, boundary_commands, (0.0, 1.0, 1.5, 2.0), clock_id="clock",
    )
    boundary_speed = boundary_trace.points[1].speed_fraction
    if (boundary_trace.points[1].command.command_id != "ramp-down"
            or boundary_speed != 1.0
            or boundary_trace.points[2].speed_fraction != 0.5):
        raise AssertionError("New target changed actuator speed before its exact start time")
    return ValidationOutcome(True, {
        "points": len(speeds),
        "final_speed_fraction": speeds[-1],
        "speed_at_command_boundary": boundary_speed,
        "boundary_command_identity": boundary_trace.points[1].command.command_id,
    }, LIMITS)


def validate_map_admission(*, work_directory, **parameters):
    model, left, right, commands = _fixture()
    trace = model.run(left, right, commands, (0.0, 0.5, 1.0, 2.0), clock_id="clock")
    assert all(p.accepted for p in trace.points)
    return ValidationOutcome(True, {"maximum_head_error": max(p.pressure_rise_relative_error for p in trace.points)}, LIMITS)


def validate_capacity_rejection(*, work_directory, **parameters):
    model, left, right, commands = _fixture()
    right.scale = 1.25
    try:
        model.run(left, right, commands, (0.0, 1.0, 2.0), clock_id="clock")
    except ValueError:
        rejected = 1
    else:
        raise AssertionError("Off-curve native point was accepted")
    return ValidationOutcome(True, {"rejected": rejected}, LIMITS)


def validate_npsh_rejection(*, work_directory, **parameters):
    model, left, right, commands = _fixture(npsh_available=-0.1)
    trace = model.run(left, right, commands, (0.0, 1.0, 2.0), clock_id="clock", require_accepted=False)
    assert any(not p.npsh_admissible for p in trace.points)
    return ValidationOutcome(True, {"minimum_margin_m": min(p.npsh_margin_m for p in trace.points)}, LIMITS)


def validate_evidence_gate(*, work_directory, **parameters):
    model, left, right, commands = _fixture()
    try:
        model.run(left, right, commands, (0.0, 1.0, 2.0), clock_id="clock", require_qualified_map=True)
    except ValueError:
        rejected = 1
    else:
        raise AssertionError("Unqualified pump map was promoted to prediction")
    return ValidationOutcome(True, {"rejected": rejected}, LIMITS)


def validate_schedule_guard(*, work_directory, **parameters):
    from h2physics.adapters.lh2dt_pump_operation import PumpSpeedCommand

    model, left, right, _ = _fixture()
    gap = (PumpSpeedCommand("a", 0.0, 0.5, 0.5), PumpSpeedCommand("b", 0.6, 1.0, 1.0))
    rejected = 0
    for commands, times in ((gap, (0.0, 0.5, 0.6, 1.0)), (_fixture()[3], (0.0, 2.0))):
        try:
            model.run(left, right, commands, times, clock_id="clock")
        except ValueError:
            rejected += 1
    assert rejected == 2
    return ValidationOutcome(True, {"rejections": rejected}, LIMITS)


def validate_command_mode(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.lh2dt_pump_operation import PumpSpeedCommand

    invalid = 0
    for mode in ("run", "stopped", "typo", ""):
        try:
            PumpSpeedCommand("mode-contract", 0., 1., .5, mode)
        except ValueError:
            invalid += 1
    assert invalid == 4
    valid = tuple(PumpSpeedCommand(f"valid-{mode}", 0., 1., target, mode)
                  for mode, target in (("operate", .5), ("hold", .5), ("stop", 0.)))
    assert tuple(command.mode for command in valid) == ("operate", "hold", "stop")
    return ValidationOutcome(True, {"invalid_modes_rejected": invalid,
                                    "valid_modes_admitted": len(valid)}, LIMITS)


def validate_original_result(*, work_directory, **parameters):
    from dataclasses import replace

    model, left, right, commands = _fixture()
    trace = model.run(left, right, commands, (0.0, 1.0, 2.0), clock_id="clock")
    assert trace.points[0].native_result is not None and trace.require_current() is trace
    direct_values = {
        name: getattr(trace, name)
        for name in type(trace).__dataclass_fields__
        if name != "_issuer_token"
    }
    rejected_unissued = 0
    for construct in (
        lambda: type(trace)(**direct_values),
        lambda: replace(trace, input_sha256="0"*64),
    ):
        try:
            construct()
        except TypeError:
            rejected_unissued += 1
    assert rejected_unissued == 2
    model.native.reference_speed_rpm = 2999.0
    try:
        trace.require_current()
    except ValueError:
        rejected = 1
    else:
        raise AssertionError("Changed native pump owner was accepted")
    return ValidationOutcome(True, {"native_points": len(trace.points), "stale_rejections": rejected,
                                    "unissued_trace_rejections": rejected_unissued}, LIMITS)


def validate_process_boundary(*, work_directory, **parameters):
    del work_directory, parameters
    from types import SimpleNamespace

    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_pump_operation import (
        FiniteSpeedPump, NormalizedPumpMap, PumpMapEvidence, PumpSpeedActuator,
        PumpSpeedCommand,
    )
    from h2physics.adapters.pump_process_boundary import pump_operation_to_process_connections

    class Provider:
        fluid = "ParaHydrogen"

        @staticmethod
        def from_ph(pressure_Pa, specific_enthalpy_J_kg):
            return SimpleNamespace(
                pressure_Pa=pressure_Pa, temperature_K=22., density_kg_m3=69.,
                specific_enthalpy_J_kg=specific_enthalpy_J_kg,
                specific_internal_energy_J_kg=specific_enthalpy_J_kg-50000.,
                specific_entropy_J_kgK=1100., quality=None, phase="liquid")

    provider = Provider()
    bridge = Lh2dtProperties(provider, reference_id="synthetic-para-H2-reference")
    inlet = SimpleNamespace(
        pressure_Pa=100000., temperature_K=20., density_kg_m3=70.,
        specific_enthalpy_J_kg=3.8e6, specific_internal_energy_J_kg=3.7e6,
        specific_entropy_J_kgK=1000., quality=None, phase="liquid")

    class Receiver:
        density_kg_m3 = 70.

        def __init__(self, pump):
            self.pump = pump

        @property
        def pressure_Pa(self):
            speed = self.pump.speed_rpm/self.pump.reference_speed_rpm
            return 100000. + 450000.*speed**2

    class Pump:
        def __init__(self):
            self.properties = provider
            self.reference_speed_rpm = 3000.
            self.speed_rpm = 1500.

        def evaluate(self, _left, right):
            speed = self.speed_rpm/self.reference_speed_rpm
            return SimpleNamespace(
                mass_flow_kg_s=.004*speed, npsh_required_m=.5*speed**2,
                npsh_available_m=5., operating_point_physical_valid=True,
                outlet_specific_enthalpy_J_kg=3.8e6+25000.*speed**2,
                outlet_pressure_Pa=right.pressure_Pa, shaft_power_W=100.*speed**3,
                momentum_residual_Pa=0.)

    pump = Pump()
    receiver = Receiver(pump)
    evidence = PumpMapEvidence("synthetic-pump-map", "fixture://pump-map", "fixture-only",
        "0"*64, provider.fluid, qualified_for_prediction=False)
    pump_map = NormalizedPumpMap("synthetic-pump", 3000., .008, 600000., .5,
        (0., .5, 1.), (1., .75, 0.), (.7, .7, .7), (1., 1., 1.), evidence)
    actuator = PumpSpeedActuator("pump-drive", "pump-boundary-clock", .5, .5, 1.,
                                 "authored-speed-command-contract")
    model = FiniteSpeedPump(pump, actuator, pump_map)
    commands = (PumpSpeedCommand("ramp", 0., 1., 1.),)
    trace = model.run(inlet, receiver, commands, (0., .5, 1.), clock_id=actuator.clock_id)
    bridge_result = pump_operation_to_process_connections(
        trace, bridge, upstream_node="source-vessel", downstream_node="transfer-line",
        source_evidence_id="authored-pump-to-line-boundary")
    assert bridge_result.require_current() is bridge_result
    assert bridge_result.time_s == (0., .5, 1.)
    assert bridge_result.clock_id == actuator.clock_id
    assert tuple(c.mass_flow_kg_s for c in bridge_result.connections) == tuple(
        point.native_result.mass_flow_kg_s for point in trace.points)
    assert bridge_result.receiver_pressures_pa == tuple(point.receiver_pressure_pa for point in trace.points)
    assert tuple(c.power.shaft_work_w for c in bridge_result.connections) == tuple(
        point.native_result.shaft_power_W for point in trace.points)
    assert all(c.upstream.basis == bridge.basis and c.transmitted.basis == bridge.basis
               for c in bridge_result.connections)
    original_power = trace.points[0].native_result.shaft_power_W
    trace.points[0].native_result.shaft_power_W = original_power + 1.
    try:
        bridge_result.require_current()
    except ValueError:
        stale_rejected = True
    else:
        raise AssertionError("Mutated accepted native pump result was reused")
    trace.points[0].native_result.shaft_power_W = original_power
    trace.require_current()
    foreign_provider_rejected = False
    try:
        pump_operation_to_process_connections(
            trace, Lh2dtProperties(Provider(), reference_id="foreign-reference"),
            upstream_node="source-vessel", downstream_node="transfer-line",
            source_evidence_id="wrong-provider-contract")
    except ValueError:
        foreign_provider_rejected = True
    assert foreign_provider_rejected
    return ValidationOutcome(True, {
        "accepted_points": len(bridge_result.connections),
        "clock_id": bridge_result.clock_id,
        "receiver_pressure_pa": list(bridge_result.receiver_pressures_pa),
        "stale_native_result_rejected": stale_rejected,
        "foreign_provider_rejected": foreign_provider_rejected,
    }, ("synthetic typed pump shaft boundary only; not motor electricity or facility qualification",))
