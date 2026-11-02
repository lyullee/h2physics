"""Bind an upper-layer H2 concentration trajectory to existing sensor/alarm models.

The compartment and vent equations remain in ``buoyant_layer``. This adapter
adds only an explicit zone-to-sensor applicability boundary and reuses the
existing first-order concentration sensor and sampled alarm logic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..buoyant_layer import (
    TwoVentHydrogenLayerConfig,
    TwoVentHydrogenLayerResult,
    run_two_vent_hydrogen_layer,
)
from ..core import Origin, finite
from .gas_detection import (
    ConcentrationAlarmConfig,
    ConcentrationAlarmEvidence,
    ConcentrationAlarmTrace,
    FirstOrderConcentrationSensorConfig,
    FirstOrderConcentrationSensorTrace,
    evaluate_concentration_alarm_from_sensor,
    evaluate_first_order_concentration_sensor,
)

_BASIS = "upper-layer-h2-mole-fraction"
_UNIT = "mol/mol"
_PENDING: set[object] = set()


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _layer_payload(result: TwoVentHydrogenLayerResult) -> tuple:
    return tuple(getattr(result, name) for name in result.__dataclass_fields__)


def _signature(value: BuoyantLayerH2AlarmHandoff) -> str:
    payload = (
        id(value.layer_result), _layer_payload(value.layer_result), repr(value.layer_config),
        value.hydrogen_mass_flow_kg_s, value.duration_s, value.maximum_step_s,
        value.clock_id, value.layer_location_id, value.release_evidence_id,
        value.source_evidence_id,
        value.zone_mapping_evidence_id, repr(value.sensor_config), repr(value.alarm_config),
        value.initial_sensor_indication, value.operating_mode_id, value.episode_id,
        id(value.sensor_response), value.sensor_response._content,
        id(value.alarm_trace), value.alarm_trace._digest,
        tuple((id(item), item._content) for item in value.trip_evidence),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BuoyantLayerH2AlarmHandoff:
    """Original buoyant-layer trace, H2 sensor response, alarm and trip evidence."""

    layer_result: TwoVentHydrogenLayerResult = field(repr=False, compare=False)
    layer_config: TwoVentHydrogenLayerConfig
    hydrogen_mass_flow_kg_s: float
    duration_s: float
    maximum_step_s: float
    clock_id: str
    layer_location_id: str
    release_evidence_id: str
    source_evidence_id: str
    zone_mapping_evidence_id: str
    sensor_config: FirstOrderConcentrationSensorConfig
    alarm_config: ConcentrationAlarmConfig
    initial_sensor_indication: float
    operating_mode_id: str
    episode_id: str
    sensor_response: FirstOrderConcentrationSensorTrace
    alarm_trace: ConcentrationAlarmTrace
    trip_evidence: tuple[ConcentrationAlarmEvidence, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING:
            raise TypeError("Issue layer alarm handoffs through evaluate_buoyant_layer_h2_alarm")
        _PENDING.remove(self._issuer_token)
        object.__setattr__(self, "trip_evidence", tuple(self.trip_evidence))
        object.__setattr__(self, "_seal", _signature(self))
        self.require_current()

    @property
    def time_s(self) -> tuple[float, ...]:
        self.require_current()
        return self.layer_result.time_s

    @property
    def true_h2_mole_fraction(self) -> tuple[float, ...]:
        self.require_current()
        return self.layer_result.upper_h2_mole_fraction

    def require_current(self):
        if (type(self.layer_result) is not TwoVentHydrogenLayerResult
                or type(self.layer_config) is not TwoVentHydrogenLayerConfig):
            raise TypeError("Retain the original two-vent hydrogen-layer result and configuration")
        if (type(self.sensor_response) is not FirstOrderConcentrationSensorTrace
                or type(self.alarm_trace) is not ConcentrationAlarmTrace):
            raise TypeError("Retain the original sampled sensor and alarm results")
        self.sensor_response.require_current()
        self.alarm_trace.require_current()
        times = self.layer_result.time_s
        concentration = self.layer_result.upper_h2_mole_fraction
        if (len(times) < 2 or len(concentration) != len(times)
                or any(b <= a for a, b in zip(times, times[1:]))
                or any(not 0. <= x <= 1. for x in concentration)):
            raise ValueError("Layer trace has an invalid H2 concentration clock")
        if (times[0] != 0. or times[-1] != self.duration_s
                or any(b-a > self.sensor_config.maximum_input_sample_gap_s
                       for a, b in zip(times, times[1:]))):
            raise ValueError("Layer clock support or sample spacing differs from sensor applicability")
        if (self.clock_id != self.sensor_config.clock_id
                or self.clock_id != self.alarm_config.clock_id
                or self.layer_location_id != self.sensor_config.location_id
                or self.layer_location_id != self.alarm_config.location_id
                or self.sensor_config.concentration_basis != _BASIS
                or self.alarm_config.concentration_basis != _BASIS
                or self.sensor_config.concentration_unit != _UNIT
                or self.alarm_config.concentration_unit != _UNIT
                or self.sensor_config.sensor_id != self.alarm_config.detector_id
                or self.sensor_config.sensor_evidence_id != self.alarm_config.sensor_evidence_id
                or self.operating_mode_id != self.alarm_config.operating_mode_id
                or self.episode_id != self.alarm_config.episode_id
                or Origin(self.alarm_config.origin) is Origin.UNRESOLVED):
            raise ValueError("Layer, detector, alarm clock/location/basis/mode must agree exactly")
        if (self.sensor_response.source_evidence_id != self.source_evidence_id
                or tuple(self.sensor_response.time_s) != times
                or tuple(self.sensor_response.true_concentration) != concentration
                or self.alarm_trace.sensor_response is not self.sensor_response):
            raise ValueError("Sensor and alarm outputs must retain the exact layer signal and clock")
        if any(type(item) is not ConcentrationAlarmEvidence for item in self.trip_evidence):
            raise TypeError("Retain evaluator-issued concentration-alarm evidence")
        active = tuple(item for item in self.alarm_trace.transitions if item.alarm_active)
        if (len(active) != len(self.trip_evidence)
                or any(item.trace is not self.alarm_trace or item.transition is not transition
                       for item, transition in zip(self.trip_evidence, active, strict=True))):
            raise ValueError("Trip evidence is detached from the original alarm trace")
        for evidence in self.trip_evidence:
            evidence.require_current()
        if self._seal and _signature(self) != self._seal:
            raise ValueError("Layer, source, detector or alarm evidence changed after issuance")
        return self


def evaluate_buoyant_layer_h2_alarm(
    layer_config: TwoVentHydrogenLayerConfig,
    *,
    hydrogen_mass_flow_kg_s: float,
    duration_s: float,
    maximum_step_s: float,
    clock_id: str,
    layer_location_id: str,
    source_evidence_id: str,
    zone_mapping_evidence_id: str,
    sensor_config: FirstOrderConcentrationSensorConfig,
    alarm_config: ConcentrationAlarmConfig,
    initial_sensor_indication: float,
    operating_mode_id: str,
    episode_id: str,
) -> BuoyantLayerH2AlarmHandoff:
    """Run the reduced H2-layer model then the declared sensor and alarm models.

    The layer concentration is a well-mixed upper-zone quantity. The caller must
    provide evidence that the physical sensor is represented by that zone scalar.
    No room-average value, spatial sensor location, detector credit, protection
    action or facility qualification is inferred.
    """
    if type(layer_config) is not TwoVentHydrogenLayerConfig:
        raise TypeError("Supply a typed two-vent hydrogen-layer configuration")
    if (type(sensor_config) is not FirstOrderConcentrationSensorConfig
            or type(alarm_config) is not ConcentrationAlarmConfig):
        raise TypeError("Supply the existing typed concentration sensor and alarm configurations")
    clock = _text(clock_id, "absolute model clock identity")
    location = _text(layer_location_id, "upper-layer zone identity")
    source_id = _text(source_evidence_id, "hydrogen release evidence")
    mapping_id = _text(zone_mapping_evidence_id, "detector-to-layer mapping evidence")
    mode = _text(operating_mode_id, "operating mode")
    episode = _text(episode_id, "release episode")
    origin = alarm_config.origin
    if (sensor_config.clock_id != clock or alarm_config.clock_id != clock
            or sensor_config.location_id != location or alarm_config.location_id != location
            or sensor_config.concentration_basis != _BASIS
            or alarm_config.concentration_basis != _BASIS
            or sensor_config.concentration_unit != _UNIT or alarm_config.concentration_unit != _UNIT
            or sensor_config.sensor_id != alarm_config.detector_id
            or sensor_config.sensor_evidence_id != alarm_config.sensor_evidence_id
            or alarm_config.operating_mode_id != mode or alarm_config.episode_id != episode):
        raise ValueError("Sensor/alarm must use the explicit layer location, clock, H2 basis and episode")
    result = run_two_vent_hydrogen_layer(
        layer_config, hydrogen_mass_flow_kg_s=hydrogen_mass_flow_kg_s,
        duration_s=duration_s, maximum_step_s=maximum_step_s,
    )
    times = result.time_s
    source = hashlib.sha256(repr((
        id(result), repr(layer_config), hydrogen_mass_flow_kg_s, duration_s,
        maximum_step_s, clock, location, source_id, mapping_id,
    )).encode("utf-8")).hexdigest()
    sensor = evaluate_first_order_concentration_sensor(
        sensor_config, time_s=times, true_concentration=result.upper_h2_mole_fraction,
        initial_indication=finite(initial_sensor_indication, "initial sensor indication"),
        source_evidence_id=source, operating_mode_id=mode, episode_id=episode,
        origin=origin,
    )
    alarm = evaluate_concentration_alarm_from_sensor(alarm_config, sensor)
    trips = tuple(ConcentrationAlarmEvidence.bind(alarm, transition)
                  for transition in alarm.transitions if transition.alarm_active)
    token = object()
    _PENDING.add(token)
    try:
        return BuoyantLayerH2AlarmHandoff(
            result, layer_config, finite(hydrogen_mass_flow_kg_s, "H2 release rate", positive=True),
            finite(duration_s, "release duration", positive=True),
            finite(maximum_step_s, "maximum integration step", positive=True),
            clock, location, source_id, source, mapping_id, sensor_config, alarm_config,
            finite(initial_sensor_indication, "initial sensor indication"), mode, episode,
            sensor, alarm, trips, token,
        ).require_current()
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["BuoyantLayerH2AlarmHandoff", "evaluate_buoyant_layer_h2_alarm"]
