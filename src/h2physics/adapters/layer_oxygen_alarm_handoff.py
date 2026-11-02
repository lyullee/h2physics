"""Source-bound upper-layer oxygen-deficit handoff to existing alarm models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

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
from .layer_oxygen_projection import LayerOxygenProjection

_PENDING_ISSUERS: set[object] = set()


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def layer_oxygen_deficit_basis(reference_evidence_id: str) -> str:
    """Return the stable concentration-basis label required by sensor/alarm configs."""
    return "upper-layer-oxygen-deficit-mole-fraction:" + _text(
        reference_evidence_id, "oxygen reference evidence ID"
    )


def _reference_fraction(value: float) -> float:
    if isinstance(value, bool):
        raise TypeError("Oxygen reference must be a mole fraction")
    result = finite(value, "oxygen reference mole fraction")
    if not 0.0 < result <= 1.0:
        raise ValueError("Oxygen reference mole fraction must lie in (0, 1]")
    return result


def _signature(result: LayerOxygenAlarmHandoff) -> str:
    projection = result.projection
    response = result.sensor_response
    alarm = result.alarm_trace
    evidence = tuple(
        (id(item), id(item.trace), id(item.transition), item._content)
        for item in result.trip_evidence
    )
    payload = (
        id(projection), projection.carrier_basis,
        projection.carrier_oxygen_mole_fraction, projection.time_s,
        projection.upper_oxygen_mole_fraction,
        result.reference_oxygen_mole_fraction, result.reference_evidence_id,
        result.reference_clock_id, result.reference_location_id,
        result.projection_clock_id, result.projection_location_id,
        result.clock_mapping_evidence_id, result.location_mapping_evidence_id,
        result.source_evidence_id, result.origin.value,
        id(result.sensor_config), repr(result.sensor_config),
        id(result.alarm_config), repr(result.alarm_config),
        result.initial_sensor_indication, result.operating_mode_id,
        result.episode_id, result.deficit_mole_fraction,
        id(response), response._content, id(response._token),
        id(alarm), alarm._digest, id(alarm._token), evidence,
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LayerOxygenAlarmHandoff:
    """Issued oxygen-deficit signal, sensor, alarm and source-bound trip evidence.

    The projection and its exact source clock remain attached. The clock and
    location mapping evidence describe caller-asserted applicability of a
    scalar oxygen reference; this adapter performs no clock conversion or
    spatial averaging.
    """

    projection: LayerOxygenProjection
    reference_oxygen_mole_fraction: float
    reference_evidence_id: str
    reference_clock_id: str
    reference_location_id: str
    projection_clock_id: str
    projection_location_id: str
    clock_mapping_evidence_id: str
    location_mapping_evidence_id: str
    source_evidence_id: str
    origin: Origin
    sensor_config: FirstOrderConcentrationSensorConfig
    alarm_config: ConcentrationAlarmConfig
    initial_sensor_indication: float
    operating_mode_id: str
    episode_id: str
    deficit_mole_fraction: tuple[float, ...]
    sensor_response: FirstOrderConcentrationSensorTrace
    alarm_trace: ConcentrationAlarmTrace
    trip_evidence: tuple[ConcentrationAlarmEvidence, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _issued_token: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise TypeError("Use evaluate_layer_oxygen_deficit_alarm to issue this handoff")
        _PENDING_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "trip_evidence", tuple(self.trip_evidence))
        object.__setattr__(self, "deficit_mole_fraction", tuple(self.deficit_mole_fraction))
        object.__setattr__(self, "_issued_token", self._issuer_token)
        self._check_outputs()
        object.__setattr__(self, "_seal", _signature(self))

    @property
    def time_s(self) -> tuple[float, ...]:
        """The exact immutable timestamp tuple retained by the projection."""
        return self.projection.time_s

    @property
    def scenario_scope(self) -> str:
        """The only supported interpretation of this handoff's signal."""
        return "upper-layer-only"

    @property
    def concentration_basis(self) -> str:
        return layer_oxygen_deficit_basis(self.reference_evidence_id)

    def _check_outputs(self) -> None:
        if type(self.projection) is not LayerOxygenProjection:
            raise TypeError("Retain an original LayerOxygenProjection")
        self.projection.require_current()
        reference = _reference_fraction(self.reference_oxygen_mole_fraction)
        for name in (
            "reference_evidence_id", "reference_clock_id", "reference_location_id",
            "projection_clock_id", "projection_location_id",
            "clock_mapping_evidence_id", "location_mapping_evidence_id",
            "source_evidence_id", "operating_mode_id", "episode_id",
        ):
            _text(getattr(self, name), name)
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Declare the origin of the upper-layer signal")
        if type(self.sensor_config) is not FirstOrderConcentrationSensorConfig:
            raise TypeError("Retain the explicit first-order sensor configuration")
        if type(self.alarm_config) is not ConcentrationAlarmConfig:
            raise TypeError("Retain the explicit concentration alarm configuration")
        basis = layer_oxygen_deficit_basis(self.reference_evidence_id)
        if (
            self.sensor_config.location_id != self.projection_location_id
            or self.sensor_config.clock_id != self.projection_clock_id
            or self.sensor_config.concentration_basis != basis
            or self.sensor_config.concentration_unit != "mole_fraction"
        ):
            raise ValueError("Sensor location, projection clock or deficit basis does not match")
        alarm = self.alarm_config
        sensor = self.sensor_config
        if (
            alarm.detector_id != sensor.sensor_id
            or alarm.location_id != self.projection_location_id
            or alarm.clock_id != self.projection_clock_id
            or alarm.concentration_basis != basis
            or alarm.concentration_unit != "mole_fraction"
            or alarm.sensor_evidence_id != sensor.sensor_evidence_id
            or alarm.operating_mode_id != self.operating_mode_id
            or alarm.episode_id != self.episode_id
            or Origin(alarm.origin) is not origin
        ):
            raise ValueError("Alarm configuration differs from the mapped source/sensor context")
        initial = finite(self.initial_sensor_indication, "initial sensor indication")
        if initial < 0.0:
            raise ValueError("Initial deficit indication must be nonnegative")

        expected = tuple(
            max(reference - float(value), 0.0)
            for value in self.projection.upper_oxygen_mole_fraction
        )
        if self.deficit_mole_fraction != expected:
            raise ValueError("Deficit samples do not reproduce the retained O2 projection")
        if len(expected) != len(self.projection.time_s):
            raise ValueError("Projection timestamps and deficit samples are not aligned")

        if type(self.sensor_response) is not FirstOrderConcentrationSensorTrace:
            raise TypeError("Retain the issued first-order sensor response")
        self.sensor_response.require_current()
        if (
            self.sensor_response.config is not sensor
            or not np.array_equal(self.sensor_response.time_s, np.asarray(self.time_s, dtype=float))
            or not np.array_equal(self.sensor_response.true_concentration,
                                  np.asarray(expected, dtype=float))
            or self.sensor_response.initial_indication != initial
            or self.sensor_response.source_evidence_id != self.source_evidence_id
            or self.sensor_response.operating_mode_id != self.operating_mode_id
            or self.sensor_response.episode_id != self.episode_id
            or Origin(self.sensor_response.origin) is not origin
        ):
            raise ValueError("Sensor response no longer matches the retained layer-deficit signal")

        if type(self.alarm_trace) is not ConcentrationAlarmTrace:
            raise TypeError("Retain the issued concentration alarm trace")
        self.alarm_trace.require_current()
        if (
            self.alarm_trace.config is not alarm
            or self.alarm_trace.sensor_response is not self.sensor_response
            or not np.array_equal(self.alarm_trace.time_s, self.sensor_response.time_s)
            or not np.array_equal(self.alarm_trace.concentration,
                                  self.sensor_response.indicated_concentration)
        ):
            raise ValueError("Alarm trace no longer follows this sensor indication")

        if any(type(item) is not ConcentrationAlarmEvidence for item in self.trip_evidence):
            raise TypeError("Retain original source-bound alarm evidence")
        active = tuple(item for item in alarm_trace_transitions(self.alarm_trace)
                       if item.alarm_active)
        if (
            len(active) != len(self.trip_evidence)
            or any(item.trace is not self.alarm_trace or item.transition is not transition
                   for item, transition in zip(self.trip_evidence, active, strict=True))
        ):
            raise ValueError("Trip evidence is detached from the retained alarm transitions")
        for item in self.trip_evidence:
            item.require_current()

    def require_current(self) -> LayerOxygenAlarmHandoff:
        if self._issuer_token is not self._issued_token:
            raise ValueError("Upper-layer oxygen alarm handoff lost its issuing identity")
        self._check_outputs()
        if _signature(self) != self._seal:
            raise ValueError("Upper-layer oxygen alarm handoff changed after issuance")
        return self


def alarm_trace_transitions(trace: ConcentrationAlarmTrace):
    """Return transitions only after the existing owner verifies its trace."""
    trace.require_current()
    return trace.transitions


def evaluate_layer_oxygen_deficit_alarm(
    projection: LayerOxygenProjection,
    *,
    reference_oxygen_mole_fraction: float,
    reference_evidence_id: str,
    reference_clock_id: str,
    reference_location_id: str,
    projection_clock_id: str,
    projection_location_id: str,
    clock_mapping_evidence_id: str,
    location_mapping_evidence_id: str,
    source_evidence_id: str,
    origin: Origin,
    sensor_config: FirstOrderConcentrationSensorConfig,
    alarm_config: ConcentrationAlarmConfig,
    initial_sensor_indication: float,
    operating_mode_id: str,
    episode_id: str,
) -> LayerOxygenAlarmHandoff:
    """Send an explicit upper-layer O2 deficit through existing sensor/alarm APIs.

    Reference/projection clock and location identifiers plus their evidence IDs
    are caller-owned applicability declarations. No clock conversion, receiver-
    room average, exposure-duration metric, or physiological response is inferred.
    """
    if type(projection) is not LayerOxygenProjection:
        raise TypeError("Supply an actual LayerOxygenProjection")
    projection.require_current()
    reference = _reference_fraction(reference_oxygen_mole_fraction)
    values = {
        "reference_evidence_id": reference_evidence_id,
        "reference_clock_id": reference_clock_id,
        "reference_location_id": reference_location_id,
        "projection_clock_id": projection_clock_id,
        "projection_location_id": projection_location_id,
        "clock_mapping_evidence_id": clock_mapping_evidence_id,
        "location_mapping_evidence_id": location_mapping_evidence_id,
        "source_evidence_id": source_evidence_id,
        "operating_mode_id": operating_mode_id,
        "episode_id": episode_id,
    }
    values = {name: _text(value, name) for name, value in values.items()}
    selected_origin = Origin(origin)
    if selected_origin is Origin.UNRESOLVED:
        raise ValueError("Declare measured, predicted, reconstructed or synthetic provenance")
    if type(sensor_config) is not FirstOrderConcentrationSensorConfig:
        raise TypeError("Supply a FirstOrderConcentrationSensorConfig")
    if type(alarm_config) is not ConcentrationAlarmConfig:
        raise TypeError("Supply a ConcentrationAlarmConfig")
    basis = layer_oxygen_deficit_basis(values["reference_evidence_id"])
    if (
        sensor_config.location_id != values["projection_location_id"]
        or sensor_config.clock_id != values["projection_clock_id"]
        or sensor_config.concentration_basis != basis
        or sensor_config.concentration_unit != "mole_fraction"
    ):
        raise ValueError("Sensor configuration must match the declared projection clock/location/basis")
    if (
        alarm_config.detector_id != sensor_config.sensor_id
        or alarm_config.location_id != values["projection_location_id"]
        or alarm_config.clock_id != values["projection_clock_id"]
        or alarm_config.concentration_basis != basis
        or alarm_config.concentration_unit != "mole_fraction"
        or alarm_config.sensor_evidence_id != sensor_config.sensor_evidence_id
        or alarm_config.operating_mode_id != values["operating_mode_id"]
        or alarm_config.episode_id != values["episode_id"]
        or Origin(alarm_config.origin) is not selected_origin
    ):
        raise ValueError("Alarm configuration does not match projection, sensor or caller context")

    initial = finite(initial_sensor_indication, "initial sensor indication")
    if initial < 0.0:
        raise ValueError("Initial deficit indication must be nonnegative")
    deficit = tuple(max(reference - float(x), 0.0)
                    for x in projection.upper_oxygen_mole_fraction)
    sensor_response = evaluate_first_order_concentration_sensor(
        sensor_config,
        time_s=projection.time_s,
        true_concentration=deficit,
        initial_indication=initial,
        source_evidence_id=values["source_evidence_id"],
        operating_mode_id=values["operating_mode_id"],
        episode_id=values["episode_id"],
        origin=selected_origin,
    )
    alarm_trace = evaluate_concentration_alarm_from_sensor(alarm_config, sensor_response)
    trip_evidence = tuple(
        ConcentrationAlarmEvidence.bind(alarm_trace, transition)
        for transition in alarm_trace.transitions if transition.alarm_active
    )

    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        result = LayerOxygenAlarmHandoff(
            projection,
            reference,
            values["reference_evidence_id"],
            values["reference_clock_id"],
            values["reference_location_id"],
            values["projection_clock_id"],
            values["projection_location_id"],
            values["clock_mapping_evidence_id"],
            values["location_mapping_evidence_id"],
            values["source_evidence_id"],
            selected_origin,
            sensor_config,
            alarm_config,
            initial,
            values["operating_mode_id"],
            values["episode_id"],
            deficit,
            sensor_response,
            alarm_trace,
            trip_evidence,
            token,
        )
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise
    return result.require_current()
