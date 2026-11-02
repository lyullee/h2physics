"""Typed handoff from current Cantera reactor composition to existing gas alarms."""

from dataclasses import dataclass, field
import hashlib

import numpy as np

from ..core import Origin

_PENDING_HANDOFFS: set[object] = set()


def _source_id(trace, species_id, location_id, clock_id, evidence_id, origin):
    digest = hashlib.sha256(repr((trace.basis, trace.constraint, species_id,
        location_id, clock_id, evidence_id, origin.value,
        trace.time_s.dtype.str, trace.time_s.shape, trace.time_s.tobytes(),
        tuple(snapshot.state.mole_fractions[species_id] for snapshot in trace.snapshots))).encode()).hexdigest()
    return "cantera-reactor-gas-mole-fraction:" + digest


@dataclass(frozen=True, slots=True)
class CanteraSpeciesAlarmHandoff:
    reactor_trace: object
    species_id: str
    location_id: str
    clock_id: str
    source_origin: Origin
    source_evidence_id: str
    source_evidence_id_input: str
    concentration_basis: str
    sensor_response: object
    alarm_trace: object
    trip_evidence: tuple
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_HANDOFFS:
            raise TypeError("Create this handoff through the Cantera gas alarm evaluator")
        _PENDING_HANDOFFS.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_seal", self._signature())

    def _signature(self):
        return hashlib.sha256(repr((id(self.reactor_trace), self.species_id,
            self.location_id, self.clock_id, self.source_origin, self.source_evidence_id,
            self.source_evidence_id_input, self.concentration_basis, id(self.sensor_response),
            getattr(self.sensor_response, "_content", None), id(self.alarm_trace),
            getattr(self.alarm_trace, "_digest", None),
            tuple((id(item), getattr(item, "_content", None)) for item in self.trip_evidence))).encode()).hexdigest()

    def require_current(self):
        from .cantera import ReactorTrace
        from .gas_detection import (
            ConcentrationAlarmEvidence, ConcentrationAlarmTrace,
            FirstOrderConcentrationSensorTrace,
        )

        if self._issuer is not self._issued:
            raise ValueError("Cantera gas handoff lost its original issuer identity")
        if type(self.reactor_trace) is not ReactorTrace:
            raise TypeError("Retain the original Cantera ReactorTrace")
        self.reactor_trace.require_current()
        if (type(self.sensor_response) is not FirstOrderConcentrationSensorTrace
                or type(self.alarm_trace) is not ConcentrationAlarmTrace):
            raise TypeError("Retain the issued sensor and alarm response objects")
        self.sensor_response.require_current()
        self.alarm_trace.require_current()
        values = np.asarray([point.state.mole_fractions[self.species_id]
                             for point in self.reactor_trace.snapshots])
        if (self.species_id not in self.reactor_trace.snapshots[0].state.mole_fractions
                or not np.array_equal(self.sensor_response.time_s, self.reactor_trace.time_s)
                or not np.array_equal(self.sensor_response.true_concentration, values)
                or self.sensor_response.source_evidence_id != self.source_evidence_id
                or self.source_evidence_id != _source_id(self.reactor_trace, self.species_id,
                    self.location_id, self.clock_id, self.source_evidence_id_input,
                    self.source_origin)
                or self.alarm_trace.sensor_response is not self.sensor_response):
            raise ValueError("Cantera species, sensor, alarm and source evidence no longer align")
        if any(type(item) is not ConcentrationAlarmEvidence for item in self.trip_evidence):
            raise ValueError("Trip outputs must be original ConcentrationAlarmEvidence")
        active = tuple(item for item in self.alarm_trace.transitions if item.alarm_active)
        if (len(active) != len(self.trip_evidence)
                or any(item.trace is not self.alarm_trace or item.transition is not transition
                       for item, transition in zip(self.trip_evidence, active, strict=True))):
            raise ValueError("Alarm trip evidence is detached from this original trace")
        for item in self.trip_evidence:
            item.require_current()
        if self._signature() != self._seal:
            raise ValueError("Cantera species handoff changed after issuance")
        return self


def evaluate_cantera_species_alarm(trace, *, species_id: str, location_id: str,
        clock_id: str, source_evidence_id: str, origin: Origin,
        sensor_config, alarm_config, initial_sensor_indication: float,
        operating_mode_id: str, episode_id: str):
    """Feed one declared gas mole fraction to existing sensor/alarm models.

    ReactorTrace has no physical site or absolute-clock premise; those identities,
    source evidence and origin must therefore be supplied explicitly by the caller.
    This adapter does not propagate a reactor composition into a room or leak field.
    """
    from .cantera import ReactorTrace
    from .gas_detection import (
        ConcentrationAlarmConfig, ConcentrationAlarmEvidence,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm_from_sensor,
        evaluate_first_order_concentration_sensor,
    )

    if type(trace) is not ReactorTrace:
        raise TypeError("Supply an original owner-issued Cantera ReactorTrace")
    trace.require_current()
    if (not all(isinstance(value, str) and value.strip() for value in
                (species_id, location_id, clock_id, source_evidence_id,
                 operating_mode_id, episode_id))):
        raise ValueError("Declare species, location, clock, source, mode and episode identities")
    if (type(sensor_config) is not FirstOrderConcentrationSensorConfig
            or type(alarm_config) is not ConcentrationAlarmConfig):
        raise TypeError("Supply existing typed first-order sensor and alarm configurations")
    origin = Origin(origin)
    if origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the reactor source origin")
    if species_id not in trace.snapshots[0].state.mole_fractions:
        raise KeyError("Selected species is absent from the original gas-phase snapshots")
    basis = "cantera-gas-phase-mole-fraction:" + species_id
    if (sensor_config.location_id != location_id or sensor_config.clock_id != clock_id
            or sensor_config.concentration_basis != basis
            or sensor_config.concentration_unit != "mole_fraction"):
        raise ValueError("Sensor location, clock or mole-fraction basis differs")
    if (alarm_config.detector_id != sensor_config.sensor_id
            or alarm_config.location_id != location_id or alarm_config.clock_id != clock_id
            or alarm_config.concentration_basis != basis
            or alarm_config.concentration_unit != "mole_fraction"
            or alarm_config.sensor_evidence_id != sensor_config.sensor_evidence_id
            or alarm_config.operating_mode_id != operating_mode_id
            or alarm_config.episode_id != episode_id or alarm_config.origin != origin):
        raise ValueError("Alarm configuration differs from the declared reactor/sensor context")
    source_id = _source_id(trace, species_id, location_id, clock_id,
                           source_evidence_id, origin)
    values = [point.state.mole_fractions[species_id] for point in trace.snapshots]
    sensor = evaluate_first_order_concentration_sensor(sensor_config,
        time_s=trace.time_s, true_concentration=values,
        initial_indication=initial_sensor_indication, source_evidence_id=source_id,
        operating_mode_id=operating_mode_id, episode_id=episode_id, origin=origin)
    alarm = evaluate_concentration_alarm_from_sensor(alarm_config, sensor)
    evidence = tuple(ConcentrationAlarmEvidence.bind(alarm, transition)
        for transition in alarm.transitions if transition.alarm_active)
    token = object()
    _PENDING_HANDOFFS.add(token)
    try:
        result = CanteraSpeciesAlarmHandoff(trace, species_id, location_id, clock_id,
            origin, source_id, source_evidence_id, basis, sensor, alarm, evidence, token)
    except Exception:
        _PENDING_HANDOFFS.discard(token)
        raise
    result.require_current()
    trace.require_current()
    return result
