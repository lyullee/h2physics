"""Deferred synthetic case for executing an alarm isolation on valve dynamics."""

from dataclasses import dataclass

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


@dataclass(frozen=True, slots=True)
class _ContractValveState:
    """Protocol-shaped state record; property values come from CoolProp."""

    pressure_Pa: float
    temperature_K: float
    density_kg_m3: float
    specific_enthalpy_J_kg: float
    specific_internal_energy_J_kg: float
    specific_entropy_J_kgK: float
    quality: float | None
    phase: str


@dataclass(frozen=True, slots=True)
class _ContractNativeValveResult:
    """Data carrier for the shared nozzle's computed fields, not a flow model."""

    mass_flow_kg_s: float
    outlet_specific_enthalpy_J_kg: float
    throat_pressure_Pa: float
    mass_flux_kg_m2_s: float
    choked: bool
    upstream_side: str | None


def _contract_state(state):
    return _ContractValveState(
        pressure_Pa=state.pressure_pa,
        temperature_K=state.temperature_k,
        density_kg_m3=state.density_kg_m3,
        specific_enthalpy_J_kg=state.enthalpy_j_kg,
        specific_internal_energy_J_kg=state.internal_energy_j_kg,
        specific_entropy_J_kgK=state.entropy_j_kg_k,
        quality=state.vapor_mass_fraction,
        phase="twophase" if state.phase == "two_phase" else state.phase,
    )


def cases():
    return (ValidationCase(
        identifier="concentration-alarm-finite-stroke-valve-actuation-trace",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_alarm_valve_actuation",
        invariants=(
            "original-confirmed-alarm-and-issued-trace-identities-retained",
            "exact-alarm-actuator-clock-and-sensor-location-applicability-required",
            "caller-sample-grid-covers-generated-command-boundaries-and-horizon",
            "existing-finite-stroke-valve-owns-actuator-physics",
            "no-detector-credit-flow-claim-or-SIS-performance-inferred",
        ),
    ),)


def validate_alarm_valve_actuation(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.alarm_valve_actuation import execute_alarm_valve_isolation
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        ConcentrationAlarmEvidence,
        evaluate_concentration_alarm,
    )
    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_equipment import Lh2dtSharedValve
    from h2physics.adapters.lh2dt_valve_actuator import (
        FiniteStrokeValve,
        StrokeActuator,
        ValveCommand,
        ValveEffectiveAreaMap,
        ValveMapEvidence,
    )
    from h2physics.core import Origin
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo.coolprop import CoolPropProperties

    clock = "synthetic-alarm-valve-clock"
    config = ConcentrationAlarmConfig(
        "synthetic-h2-detector", "compressor-room", clock,
        "normal-operation", "episode-7", "dry mole fraction", "mol/mol",
        0.01, 0.005, 2, 2, 0.5, "synthetic-sensor", "synthetic-trip-limit",
        "synthetic-alarm-logic", Origin.SYNTHETIC,
    )
    alarm_trace = evaluate_concentration_alarm(
        config, time_s=(0., 0.5, 1., 1.5),
        concentration=(0.001, 0.012, 0.014, 0.008),
    )
    alarm = ConcentrationAlarmEvidence.bind(
        alarm_trace, next(item for item in alarm_trace.transitions if item.alarm_active),
    )
    properties = CoolPropProperties("Hydrogen")
    # Lh2dtProperties reads this descriptive fluid label; the case only uses its
    # internal state bridge and never imports the external `lh2dt` package.
    properties.fluid = "Hydrogen"
    bridge = Lh2dtProperties(
        properties, reference_id=properties.basis.reference_id,
    )
    shared_valve = Lh2dtSharedValve(
        HomogeneousIsentropicNozzle(properties),
        bridge,
        NozzleOpening.circular(
            "synthetic-compressor-isolation-opening", 0.0003,
            effective_area_factor=0.8,
            area_basis_id="synthetic-effective-area-only",
        ),
        result_factory=_ContractNativeValveResult,
        opening_fraction=0.0,
        allow_reverse=False,
    )
    evidence = ValveMapEvidence(
        evidence_id="synthetic-actuator-map-evidence",
        source_uri="urn:h2physics:synthetic-actuator-map",
        license_id="synthetic-only",
        source_sha256="0" * 64,
        fluid_basis=properties.basis.fluid,
    )
    area_map = ValveEffectiveAreaMap(
        "synthetic-actuator-area-map",
        (0.0, 0.25, 0.5, 0.75, 1.0),
        (0.0, 0.03, 0.12, 0.38, 1.0),
        evidence,
    )
    actuator = StrokeActuator(
        "synthetic-finite-stroke-actuator",
        opening_rate_fraction_s=2.0,
        closing_rate_fraction_s=4.0,
        initial_stroke_fraction=0.0,
        clock_id=clock,
        evidence_id="synthetic-rates-not-hardware-qualified",
    )
    valve = FiniteStrokeValve(shared_valve, actuator, area_map)
    left = _contract_state(properties.state_pt(3e6, 300.0))
    right = _contract_state(properties.state_pt(1e6, 300.0))
    source = (
        ValveCommand(0., 1., 0.35, "normal-0"),
        ValveCommand(1., 2., 0.55, "normal-1"),
        ValveCommand(2., 4., 0.7, "normal-2"),
    )
    grid = (0., 0.5, 1., 1.2, 1.5, 2., 3.)
    result = execute_alarm_valve_isolation(
        alarm, valve, left, right, source, grid,
        clock_id=clock,
        mapped_sensor_location_ids=("compressor-room",),
        physical_valve_id="synthetic-compressor-isolation-valve",
        actuator_id=actuator.actuator_id,
        location_mapping_evidence_id="synthetic-location-map",
        latency_s=0.2, isolation_end_s=3., command_prefix="synthetic-trip",
        action_evidence_id="synthetic-isolation-action",
    )
    assert result.alarm_evidence is alarm
    assert result.trace.owner is valve
    assert tuple(point.time_s for point in result.trace.points) == grid
    assert tuple(point.command.command_id for point in result.trace.points) == (
        "normal-0", "normal-0", "normal-1", "synthetic-trip:isolate",
        "synthetic-trip:isolate", "synthetic-trip:isolate", "synthetic-trip:isolate",
    )
    assert result.trace.points[-1].stroke_fraction == 0.
    result.require_current()

    rejected = 0
    invalid_cases = (
        {"clock_id": "different-clock"},
        {"mapped_sensor_location_ids": ("other-room",)},
    )
    base = dict(
        clock_id=clock, mapped_sensor_location_ids=("compressor-room",),
        physical_valve_id="synthetic-compressor-isolation-valve",
        actuator_id=actuator.actuator_id,
        location_mapping_evidence_id="synthetic-location-map",
        latency_s=0.2, isolation_end_s=3., command_prefix="rejected-trip",
        action_evidence_id="synthetic-isolation-action",
    )
    for overrides in invalid_cases:
        arguments = dict(base)
        arguments.update(overrides)
        try:
            execute_alarm_valve_isolation(alarm, valve, left, right, source, grid, **arguments)
        except ValueError:
            rejected += 1
    try:
        execute_alarm_valve_isolation(
            alarm, valve, left, right, source, (0., 0.5, 1., 1.2, 1.5, 2., 2.9),
            **base,
        )
    except ValueError:
        rejected += 1
    assert rejected == 3
    return ValidationOutcome(True, {
        "alarm_time_s": alarm.time_s,
        "trace_sample_count": len(result.trace.points),
        "final_stroke_fraction": result.trace.points[-1].stroke_fraction,
        "rejected_invalid_bindings": rejected,
    }, (
        "Synthetic integration contract only; actuator rates are authored and unqualified.",
        "No detector credit, safety instrumented function or flow safety claim is made.",
    ))
