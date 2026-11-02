"""Typed boundary from a finite oxygen-room run to existing detector/alarm logic."""

from dataclasses import dataclass, field
import hashlib

import numpy as np

from ..core import Origin, finite

_PENDING_HANDOFF_ISSUERS: set[object] = set()


def _room_source_id(room_result, reference, reference_evidence_id):
    region = room_result.region
    digest = hashlib.sha256(repr((room_result.source_definition_sha256,
        room_result.source_sha256, region, reference, reference_evidence_id,
        room_result.time_s.dtype.str, room_result.time_s.shape,
        room_result.time_s.tobytes(), room_result.dry_oxygen_mole_fraction.dtype.str,
        room_result.dry_oxygen_mole_fraction.shape,
        room_result.dry_oxygen_mole_fraction.tobytes())).encode()).hexdigest()
    return "oxygen-room-dry-deficit:" + digest


@dataclass(frozen=True, slots=True)
class OxygenDeficitAlarmHandoff:
    room_result: object
    sensor_response: object
    alarm_trace: object
    trip_evidence: tuple
    reference_dry_oxygen_mole_fraction: float
    reference_evidence_id: str
    source_evidence_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)
    _issued_token: object = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_HANDOFF_ISSUERS:
            raise TypeError("Create oxygen alarm handoffs through the typed evaluator")
        _PENDING_HANDOFF_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issued_token", self._issuer_token)
        object.__setattr__(self, "_seal", self._signature())

    def _signature(self):
        evidence = tuple((id(item), item._content) for item in self.trip_evidence)
        return hashlib.sha256(repr((id(self.room_result), id(self.sensor_response),
            getattr(self.sensor_response, "_content", None), id(self.alarm_trace),
            getattr(self.alarm_trace, "_digest", None), evidence,
            self.reference_dry_oxygen_mole_fraction, self.reference_evidence_id,
            self.source_evidence_id)).encode()).hexdigest()

    def require_current(self):
        from .oxygen_deficiency import verify_oxygen_room_result
        from .gas_detection import (
            ConcentrationAlarmEvidence, ConcentrationAlarmTrace,
            FirstOrderConcentrationSensorTrace,
        )

        if self._issuer_token is not self._issued_token:
            raise ValueError("Oxygen alarm handoff no longer has its issuing identity")
        verify_oxygen_room_result(self.room_result)
        if (type(self.sensor_response) is not FirstOrderConcentrationSensorTrace
                or type(self.alarm_trace) is not ConcentrationAlarmTrace):
            raise ValueError("Oxygen alarm handoff requires original sensor and alarm traces")
        self.sensor_response.require_current()
        self.alarm_trace.require_current()
        expected = np.maximum(self.reference_dry_oxygen_mole_fraction
                              - self.room_result.dry_oxygen_mole_fraction, 0.)
        if (not np.all(self.room_result.dry_fraction_valid)
                or not np.array_equal(self.sensor_response.time_s, self.room_result.time_s)
                or not np.array_equal(self.sensor_response.true_concentration, expected)
                or self.sensor_response.source_evidence_id != self.source_evidence_id
                or self.source_evidence_id != _room_source_id(self.room_result,
                    self.reference_dry_oxygen_mole_fraction, self.reference_evidence_id)
                or self.alarm_trace.sensor_response is not self.sensor_response):
            raise ValueError("Oxygen deficit, sensor, alarm and source output no longer align")
        if any(type(item) is not ConcentrationAlarmEvidence for item in self.trip_evidence):
            raise ValueError("Trip outputs must be original source-bound alarm evidence")
        active = tuple(item for item in self.alarm_trace.transitions if item.alarm_active)
        if (len(active) != len(self.trip_evidence)
                or any(evidence.trace is not self.alarm_trace
                       or evidence.transition is not transition
                       for evidence, transition in zip(self.trip_evidence, active, strict=True))):
            raise ValueError("Trip evidence is detached from the retained oxygen-deficit alarm")
        for item in self.trip_evidence:
            item.require_current()
        if self._signature() != self._seal:
            raise ValueError("Oxygen alarm handoff identity or evidence changed after issuance")
        return self


def evaluate_oxygen_deficit_alarm(room_result, *, sensor_config, alarm_config,
        reference_dry_oxygen_mole_fraction: float, reference_evidence_id: str,
        initial_sensor_indication: float, operating_mode_id: str, episode_id: str):
    """Project room dry-O2 output to a deficit signal and run existing detector logic.

    Deficit is max(reference dry-O2 minus room dry-O2, 0), in mole fraction. This
    adapter does not choose the ambient reference, detector response, setpoints,
    confirmation rule or human consequence; all are supplied as explicit inputs.
    """
    from .oxygen_deficiency import OxygenRoomResult, verify_oxygen_room_result
    from .gas_detection import (
        ConcentrationAlarmConfig, ConcentrationAlarmEvidence,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm_from_sensor,
        evaluate_first_order_concentration_sensor,
    )

    if type(room_result) is not OxygenRoomResult:
        raise TypeError("Supply an owner-issued finite Cantera oxygen-room result")
    verify_oxygen_room_result(room_result)
    if (type(sensor_config) is not FirstOrderConcentrationSensorConfig
            or type(alarm_config) is not ConcentrationAlarmConfig):
        raise TypeError("Supply existing typed sensor and alarm configurations")
    reference = finite(reference_dry_oxygen_mole_fraction, "reference dry oxygen mole fraction")
    if not 0 < reference <= 1:
        raise ValueError("Reference dry oxygen mole fraction must lie in (0,1]")
    if (not isinstance(reference_evidence_id, str) or not reference_evidence_id.strip()
            or not isinstance(operating_mode_id, str) or not operating_mode_id.strip()
            or not isinstance(episode_id, str) or not episode_id.strip()):
        raise ValueError("Reference, operating-mode and episode evidence are required")
    region = room_result.region
    if (not np.all(room_result.dry_fraction_valid)
            or not np.all(np.isfinite(room_result.dry_oxygen_mole_fraction))):
        raise ValueError("Undefined dry oxygen fractions cannot feed detector response")
    basis = "dry-oxygen-deficit-mole-fraction:" + reference_evidence_id.strip()
    if (sensor_config.location_id != region.region_id
            or sensor_config.clock_id != region.clock_id
            or sensor_config.concentration_basis != basis
            or sensor_config.concentration_unit != "mole_fraction"):
        raise ValueError("Sensor identity, clock, location or deficit basis differs from room output")
    if (alarm_config.detector_id != sensor_config.sensor_id
            or alarm_config.location_id != region.region_id
            or alarm_config.clock_id != region.clock_id
            or alarm_config.concentration_basis != basis
            or alarm_config.concentration_unit != "mole_fraction"
            or alarm_config.sensor_evidence_id != sensor_config.sensor_evidence_id
            or alarm_config.operating_mode_id != operating_mode_id
            or alarm_config.episode_id != episode_id
            or alarm_config.origin != region.origin):
        raise ValueError("Alarm configuration differs from room, sensor, episode or deficit basis")
    source_id = _room_source_id(room_result, reference, reference_evidence_id.strip())
    deficit = np.maximum(reference-room_result.dry_oxygen_mole_fraction, 0.)
    sensor = evaluate_first_order_concentration_sensor(sensor_config,
        time_s=room_result.time_s, true_concentration=deficit,
        initial_indication=initial_sensor_indication, source_evidence_id=source_id,
        operating_mode_id=operating_mode_id, episode_id=episode_id,
        origin=Origin(region.origin))
    alarm = evaluate_concentration_alarm_from_sensor(alarm_config, sensor)
    evidence = tuple(ConcentrationAlarmEvidence.bind(alarm, transition)
        for transition in alarm.transitions if transition.alarm_active)
    token = object()
    _PENDING_HANDOFF_ISSUERS.add(token)
    try:
        result = OxygenDeficitAlarmHandoff(room_result, sensor, alarm, evidence,
            reference, reference_evidence_id.strip(), source_id, token)
    except Exception:
        _PENDING_HANDOFF_ISSUERS.discard(token)
        raise
    result.require_current()
    verify_oxygen_room_result(room_result)
    return result
