"""Bind an admitted steady preferred plume to the existing sampled alarm chain.

This adapter owns only typed handoff/provenance. It does not interpolate spatial
fields, evolve a plume, solve detector physics, or grant protection credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

import numpy as np

from ..core import finite
from ..dispersion import HydrogenReleaseFamily
from .facility_accident_chain import FacilityDispersionHandoff
from .gas_detection import (
    ConcentrationAlarmConfig,
    ConcentrationAlarmEvidence,
    ConcentrationAlarmTrace,
    FirstOrderConcentrationSensorConfig,
    FirstOrderConcentrationSensorTrace,
    evaluate_concentration_alarm_from_sensor,
    evaluate_first_order_concentration_sensor,
)

_CONCENTRATION_BASIS = "preferred-dispersion-h2-mole-fraction"


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PreferredDispersionReceptor:
    """A caller-positioned receptor with explicit coordinate provenance."""

    receptor_id: str
    frame_id: str
    clock_id: str
    position_m: tuple[float, float, float]
    position_evidence_id: str

    def __post_init__(self):
        for name in ("receptor_id", "frame_id", "clock_id", "position_evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        position = tuple(finite(value, "receptor position") for value in self.position_m)
        if len(position) != 3:
            raise ValueError("Receptor position must have three coordinates in its declared frame")
        object.__setattr__(self, "position_m", position)


def _source_state(handoff):
    if type(handoff) is not FacilityDispersionHandoff:
        raise TypeError("Supply an admitted FacilityDispersionHandoff")
    handoff.require_current()
    if handoff.family not in (
        HydrogenReleaseFamily.HIGH_PRESSURE_GAS,
        HydrogenReleaseFamily.LIQUID_HYDROGEN_ORIGIN,
    ):
        raise ValueError("Only the preferred high-pressure-gas and LH2-origin routes are supported")
    source = handoff.finite_source.source
    source.require_current()
    edges = np.asarray(source.edges_s, dtype=float)
    masses = np.asarray(source.mass_kg, dtype=float)
    widths = np.diff(edges)
    if edges.ndim != 1 or len(edges) < 2 or masses.ndim != 1 or len(masses) != len(widths):
        raise ValueError("Facility source must retain aligned finite intervals")
    rates = masses / widths
    if np.any(~np.isfinite(rates)) or np.any(rates <= 0.0):
        raise ValueError("A steady receptor field requires a positive source rate in every interval")
    absolute_rate_tolerance = handoff.mass_absolute_tolerance_kg / float(edges[-1] - edges[0])
    if not np.allclose(rates, rates[0], rtol=1e-10, atol=absolute_rate_tolerance):
        raise ValueError("A steady preferred-dispersion result cannot represent varying source-bin rates")
    return source, tuple(float(value) for value in edges)


@dataclass(frozen=True, slots=True)
class PreferredDispersionReceptorField:
    """One caller-projected steady H2 mole fraction over a finite source window."""

    handoff: FacilityDispersionHandoff = dataclass_field(repr=False, compare=False)
    receptor: PreferredDispersionReceptor
    clock_id: str
    h2_mole_fraction: float
    receptor_mapping_evidence_id: str
    steady_window_evidence_id: str
    _seal: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.handoff) is not FacilityDispersionHandoff:
            raise TypeError("Retain the original preferred-dispersion facility handoff")
        self.handoff.require_current()
        if type(self.receptor) is not PreferredDispersionReceptor:
            raise TypeError("Supply a typed fixed receptor and position evidence")
        _source_state(self.handoff)
        source = self.handoff.finite_source.source
        if (self.receptor.frame_id != source.location.coordinate_frame_id
                or self.clock_id != source.location.clock_id):
            raise ValueError("Receptor frame and clock must match the exact admitted finite source")
        clock = _text(self.clock_id, "receptor clock")
        concentration = finite(self.h2_mole_fraction, "receptor H2 mole fraction")
        if not 0.0 <= concentration <= 1.0:
            raise ValueError("H2 mole fraction must lie in [0, 1]")
        mapping = _text(self.receptor_mapping_evidence_id, "receptor field mapping evidence")
        steady = _text(self.steady_window_evidence_id, "steady-field-over-window evidence")
        object.__setattr__(self, "clock_id", clock)
        object.__setattr__(self, "h2_mole_fraction", concentration)
        object.__setattr__(self, "receptor_mapping_evidence_id", mapping)
        object.__setattr__(self, "steady_window_evidence_id", steady)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (
            id(self.handoff), id(self.receptor), self.clock_id,
            self.h2_mole_fraction, self.receptor_mapping_evidence_id,
            self.steady_window_evidence_id,
        )

    @property
    def time_s(self) -> tuple[float, ...]:
        self.require_current()
        return _source_state(self.handoff)[1]

    @property
    def concentration_mole_fraction(self) -> tuple[float, ...]:
        self.require_current()
        return (self.h2_mole_fraction,) * len(_source_state(self.handoff)[1])

    def require_current(self):
        self.handoff.require_current()
        if self._content() != self._seal:
            raise ValueError("Receptor, clock, projection or steady-window evidence changed")
        _source_state(self.handoff)
        return self


def bind_preferred_dispersion_receptor_field(
    handoff: FacilityDispersionHandoff,
    receptor: PreferredDispersionReceptor,
    h2_mole_fraction: float,
    *,
    expected_family: HydrogenReleaseFamily,
    expected_source_domain_id: str,
    clock_id: str,
    receptor_mapping_evidence_id: str,
    steady_window_evidence_id: str,
) -> PreferredDispersionReceptorField:
    """Bind a caller-extracted steady plume value to the exact admitted provider.

    The caller owns spatial sampling/interpolation and must provide evidence for
    that mapping. The same field value is held only over the source's exact time
    edges, and only when all source-bin rates are constant within the handoff's
    declared mass tolerance. This introduces no plume memory or startup physics.
    """
    if type(handoff) is not FacilityDispersionHandoff:
        raise TypeError("Supply an admitted FacilityDispersionHandoff")
    handoff.require_current()
    family = HydrogenReleaseFamily(expected_family)
    domain_id = _text(expected_source_domain_id, "caller-declared source domain")
    source = handoff.finite_source.source
    if handoff.family is not family:
        raise ValueError("Preferred-provider family differs from the caller-declared source family")
    if source.location.source_id != domain_id:
        raise ValueError("Preferred-provider source domain differs from the caller declaration")
    if receptor.frame_id != source.location.coordinate_frame_id:
        raise ValueError("Receptor frame differs from the admitted finite-source coordinate frame")
    if receptor.clock_id != clock_id:
        raise ValueError("Receptor and sampled-field clocks must match")
    return PreferredDispersionReceptorField(
        handoff, receptor, clock_id, h2_mole_fraction,
        receptor_mapping_evidence_id, steady_window_evidence_id,
    ).require_current()


@dataclass(frozen=True, slots=True)
class PreferredDispersionAlarmHandoff:
    """Exact provider field, sensor response, sampled alarm and confirmed trips."""

    field: PreferredDispersionReceptorField = dataclass_field(repr=False, compare=False)
    sensor_response: FirstOrderConcentrationSensorTrace = dataclass_field(repr=False, compare=False)
    alarm_trace: ConcentrationAlarmTrace = dataclass_field(repr=False, compare=False)
    trip_evidence: tuple[ConcentrationAlarmEvidence, ...]
    source_evidence_id: str
    _seal: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.field) is not PreferredDispersionReceptorField:
            raise TypeError("Retain the original typed preferred-dispersion receptor field")
        self.field.require_current()
        if (type(self.sensor_response) is not FirstOrderConcentrationSensorTrace
                or type(self.alarm_trace) is not ConcentrationAlarmTrace):
            raise TypeError("Retain the original sensor and alarm engine results")
        self.sensor_response.require_current()
        self.alarm_trace.require_current()
        trips = tuple(self.trip_evidence)
        if any(type(item) is not ConcentrationAlarmEvidence for item in trips):
            raise TypeError("Alarm trips must be original source-bound ConcentrationAlarmEvidence")
        source_id = _text(self.source_evidence_id, "dispersion source evidence")
        object.__setattr__(self, "trip_evidence", trips)
        object.__setattr__(self, "source_evidence_id", source_id)
        object.__setattr__(self, "_seal", self._content())
        self.require_current()

    def _content(self):
        return (
            id(self.field), id(self.sensor_response), id(self.alarm_trace),
            tuple(id(item) for item in self.trip_evidence), self.source_evidence_id,
        )

    def require_current(self):
        self.field.require_current()
        self.sensor_response.require_current()
        self.alarm_trace.require_current()
        if self._content() != self._seal:
            raise ValueError("Preferred-dispersion alarm chain changed after issue")
        times = np.asarray(self.field.time_s, dtype=float)
        values = np.asarray(self.field.concentration_mole_fraction, dtype=float)
        config = self.sensor_response.config
        if (not np.array_equal(self.sensor_response.time_s, times)
                or not np.array_equal(self.sensor_response.true_concentration, values)
                or self.sensor_response.source_evidence_id != self.source_evidence_id
                or self.alarm_trace.sensor_response is not self.sensor_response
                or config.location_id != self.field.receptor.receptor_id
                or config.clock_id != self.field.clock_id
                or config.concentration_basis != _CONCENTRATION_BASIS
                or config.concentration_unit != "mole_fraction"):
            raise ValueError("Provider, receptor, clock, sensor and alarm signal no longer align")
        active = tuple(item for item in self.alarm_trace.transitions if item.alarm_active)
        if (len(active) != len(self.trip_evidence)
                or any(item.trace is not self.alarm_trace or item.transition is not transition
                       for item, transition in zip(self.trip_evidence, active, strict=True))):
            raise ValueError("Trip evidence is detached from the original alarm transitions")
        for item in self.trip_evidence:
            item.require_current()
        return self


def evaluate_preferred_dispersion_alarm(
    field: PreferredDispersionReceptorField,
    *,
    sensor_config: FirstOrderConcentrationSensorConfig,
    alarm_config: ConcentrationAlarmConfig,
    initial_sensor_indication: float,
    operating_mode_id: str,
    episode_id: str,
) -> PreferredDispersionAlarmHandoff:
    """Reuse existing sampled sensor/alarm models for an admitted steady field.

    A steady native field is held over the exact finite-source window. Callers
    remain responsible for receptor extraction and applicability evidence; this
    convenience does not convert independent snapshots into a transient plume.
    """
    if type(field) is not PreferredDispersionReceptorField:
        raise TypeError("Supply a typed preferred-dispersion receptor field")
    field.require_current()
    for value, name in ((operating_mode_id, "operating mode"), (episode_id, "episode")):
        _text(value, name)
    if (type(sensor_config) is not FirstOrderConcentrationSensorConfig
            or type(alarm_config) is not ConcentrationAlarmConfig):
        raise TypeError("Supply existing typed first-order sensor and alarm configurations")
    receptor = field.receptor
    if (sensor_config.location_id != receptor.receptor_id
            or sensor_config.clock_id != field.clock_id
            or sensor_config.concentration_basis != _CONCENTRATION_BASIS
            or sensor_config.concentration_unit != "mole_fraction"):
        raise ValueError("Sensor location, clock, basis and units must match the receptor field")
    if (alarm_config.detector_id != sensor_config.sensor_id
            or alarm_config.location_id != receptor.receptor_id
            or alarm_config.clock_id != field.clock_id
            or alarm_config.concentration_basis != _CONCENTRATION_BASIS
            or alarm_config.concentration_unit != "mole_fraction"
            or alarm_config.sensor_evidence_id != sensor_config.sensor_evidence_id
            or alarm_config.operating_mode_id != operating_mode_id
            or alarm_config.episode_id != episode_id
            or alarm_config.origin != field.handoff.finite_source.source.origin):
        raise ValueError("Alarm configuration differs from the declared provider/receptor context")
    source_ids = field.handoff.execution.source_evidence_ids
    if not source_ids:
        raise ValueError("Preferred dispersion receipt has no source evidence identity")
    source_id = "|".join((
        field.handoff.evidence_id,
        field.handoff.execution.provider_id,
        *source_ids,
        receptor.position_evidence_id,
        field.receptor_mapping_evidence_id,
        field.steady_window_evidence_id,
    ))
    sensor = evaluate_first_order_concentration_sensor(
        sensor_config,
        time_s=field.time_s,
        true_concentration=field.concentration_mole_fraction,
        initial_indication=initial_sensor_indication,
        source_evidence_id=source_id,
        operating_mode_id=operating_mode_id,
        episode_id=episode_id,
        origin=field.handoff.finite_source.source.origin,
    )
    alarm = evaluate_concentration_alarm_from_sensor(alarm_config, sensor)
    trips = tuple(
        ConcentrationAlarmEvidence.bind(alarm, transition)
        for transition in alarm.transitions
        if transition.alarm_active
    )
    result = PreferredDispersionAlarmHandoff(field, sensor, alarm, trips, source_id)
    field.require_current()
    result.require_current()
    return result


__all__ = [
    "PreferredDispersionReceptor",
    "PreferredDispersionReceptorField",
    "PreferredDispersionAlarmHandoff",
    "bind_preferred_dispersion_receptor_field",
    "evaluate_preferred_dispersion_alarm",
]
