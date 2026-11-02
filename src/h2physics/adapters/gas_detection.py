"""First-order concentration indication and sampled alarm logic.

The sensor layer represents only a caller-parameterized first-order lag. It does
not model sensing chemistry, cross-sensitivity, saturation, noise, communication
delay, detector reliability, setpoint choice, or facility safety performance.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import exp, fsum
from types import MappingProxyType

import numpy as np

from ..core import Origin, finite, immutable_array

_PENDING_TRACE_ISSUERS: set[object] = set()
_PENDING_EVENT_ISSUERS: set[object] = set()
_PENDING_SENSOR_ISSUERS: set[object] = set()


def _consume_issuer(token: object, pending: set[object], description: str) -> None:
    if token not in pending:
        raise TypeError(f"Use the native evaluator to issue {description}")
    pending.remove(token)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _digest(config, time_s, concentration, latched, events, sensor_response=None):
    digest = hashlib.sha256(repr(config).encode("utf-8"))
    for array in (time_s, concentration, latched):
        contiguous = np.ascontiguousarray(array)
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(repr(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    digest.update(repr(events).encode("utf-8"))
    if sensor_response is not None:
        digest.update(repr((id(sensor_response), id(sensor_response._token))).encode("ascii"))
        digest.update(sensor_response._content.encode("ascii"))
    return digest.hexdigest()


def _sensor_digest(config, time_s, actual, indicated, initial, source_id,
                   operating_mode_id, episode_id, origin):
    digest = hashlib.sha256(repr((config, initial, source_id, operating_mode_id,
                                 episode_id, origin.value)).encode("utf-8"))
    for array in (time_s, actual, indicated):
        contiguous = np.ascontiguousarray(array)
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(repr(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class FirstOrderConcentrationSensorConfig:
    """Caller-qualified first-order response on the input concentration basis."""

    sensor_id: str
    location_id: str
    clock_id: str
    concentration_basis: str
    concentration_unit: str
    response_time_constant_s: float
    maximum_input_sample_gap_s: float
    sensor_evidence_id: str
    response_parameter_evidence_id: str
    model_evidence_id: str

    def __post_init__(self):
        for name in (
            "sensor_id", "location_id", "clock_id", "concentration_basis",
            "concentration_unit", "sensor_evidence_id",
            "response_parameter_evidence_id", "model_evidence_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "response_time_constant_s", finite(
            self.response_time_constant_s, "sensor response time constant", positive=True
        ))
        object.__setattr__(self, "maximum_input_sample_gap_s", finite(
            self.maximum_input_sample_gap_s, "maximum input sample gap", positive=True
        ))


def _first_order_indication(config, time_s, actual, initial):
    if time_s.ndim != 1 or actual.shape != time_s.shape or not len(time_s):
        raise ValueError("Sensor input time and concentration must be aligned nonempty vectors")
    if (not np.all(np.isfinite(time_s)) or not np.all(np.isfinite(actual))
            or np.any(time_s < 0) or np.any(actual < 0)):
        raise ValueError("Sensor input time and true concentration must be finite and nonnegative")
    indication = np.empty_like(actual)
    indication[0] = initial
    for i in range(1, len(time_s)):
        dt = float(time_s[i] - time_s[i - 1])
        if dt <= 0:
            raise ValueError("Sensor input sample times must increase strictly")
        if dt > config.maximum_input_sample_gap_s:
            raise ValueError("Sensor input gap exceeds its declared maximum")
        x = dt / config.response_time_constant_s
        if x > 745.:
            decay, old_weight, new_weight = 0., 0., 1.
        elif x < 1e-4:
            x2 = x * x
            x3 = x2 * x
            x4 = x3 * x
            new_weight = x / 2. - x2 / 6. + x3 / 24. - x4 / 120.
            old_weight = x / 2. - x2 / 3. + x3 / 8. - x4 / 30.
            decay = exp(-x)
        else:
            decay = exp(-x)
            ratio = -np.expm1(-x) / x
            new_weight = 1. - ratio
            old_weight = ratio - decay
        value = fsum((decay * float(indication[i - 1]),
                      old_weight * float(actual[i - 1]),
                      new_weight * float(actual[i])))
        if not np.isfinite(value) or value < 0:
            raise ValueError("First-order sensor response produced an invalid concentration")
        indication[i] = value
    return indication


@dataclass(frozen=True, slots=True)
class FirstOrderConcentrationSensorTrace:
    """Issued first-order indication retaining the exact true input history."""

    config: FirstOrderConcentrationSensorConfig
    time_s: np.ndarray
    true_concentration: np.ndarray
    indicated_concentration: np.ndarray
    initial_indication: float
    source_evidence_id: str
    operating_mode_id: str
    episode_id: str
    origin: Origin
    _content: str = field(repr=False)
    _token: object = field(repr=False)
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        _consume_issuer(self._token, _PENDING_SENSOR_ISSUERS, "a first-order sensor trace")
        if type(self.config) is not FirstOrderConcentrationSensorConfig:
            raise TypeError("Retain the explicit first-order sensor configuration")
        object.__setattr__(self, "time_s", immutable_array(self.time_s, dtype=float, name="sensor time"))
        object.__setattr__(self, "true_concentration", immutable_array(
            self.true_concentration, dtype=float, name="true concentration"
        ))
        object.__setattr__(self, "indicated_concentration", immutable_array(
            self.indicated_concentration, dtype=float, name="indicated concentration"
        ))
        initial = finite(self.initial_indication, "initial sensor indication")
        if initial < 0:
            raise ValueError("Initial sensor indication must be nonnegative")
        object.__setattr__(self, "initial_indication", initial)
        object.__setattr__(self, "source_evidence_id", _text(self.source_evidence_id, "source evidence"))
        object.__setattr__(self, "operating_mode_id", _text(self.operating_mode_id, "operating mode"))
        object.__setattr__(self, "episode_id", _text(self.episode_id, "episode"))
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("Declare the source origin for the concentration history")
        object.__setattr__(self, "origin", origin)
        expected = _first_order_indication(self.config, self.time_s,
                                           self.true_concentration, initial)
        if (not np.array_equal(self.indicated_concentration, expected)
                or self._content != _sensor_digest(
                    self.config, self.time_s, self.true_concentration,
                    self.indicated_concentration, initial, self.source_evidence_id,
                    self.operating_mode_id, self.episode_id, origin
                )):
            raise ValueError("Sensor indication does not reproduce its retained input and model")
        object.__setattr__(self, "_issued_token", self._token)

    def require_current(self):
        if self._token is not self._issued_token:
            raise ValueError("Sensor trace was not issued by the response evaluator")
        expected = _first_order_indication(
            self.config, self.time_s, self.true_concentration, self.initial_indication
        )
        if (not np.array_equal(self.indicated_concentration, expected)
                or self._content != _sensor_digest(
                    self.config, self.time_s, self.true_concentration,
                    self.indicated_concentration, self.initial_indication,
                    self.source_evidence_id, self.operating_mode_id,
                    self.episode_id, self.origin
                )):
            raise ValueError("Sensor trace or its retained input changed after evaluation")
        return self


def evaluate_first_order_concentration_sensor(
    config, *, time_s, true_concentration, initial_indication,
    source_evidence_id, operating_mode_id, episode_id, origin,
):
    """Filter piecewise-linear true concentration with a closed-form first-order lag.

    The caller supplies the complete input clock, source identity and initial
    indication. The signal is assumed linear between adjacent input samples; no
    sensor dead time, calibration correction, clipping, noise or missing-data fill
    is applied.
    """
    if type(config) is not FirstOrderConcentrationSensorConfig:
        raise TypeError("Supply an explicit first-order sensor configuration")
    try:
        raw_time, raw_actual = np.asarray(time_s), np.asarray(true_concentration)
        if raw_time.dtype.kind not in "iuf" or raw_actual.dtype.kind not in "iuf":
            raise ValueError("Sensor time and true concentration require real samples")
        time = np.asarray(raw_time, dtype=float)
        actual = np.asarray(raw_actual, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("Sensor time and true concentration require real samples") from error
    initial = finite(initial_indication, "initial sensor indication")
    if initial < 0:
        raise ValueError("Initial sensor indication must be nonnegative")
    source_id = _text(source_evidence_id, "source evidence")
    mode_id = _text(operating_mode_id, "operating mode")
    selected_episode_id = _text(episode_id, "episode")
    source_origin = Origin(origin)
    if source_origin == Origin.UNRESOLVED:
        raise ValueError("Declare measured, predicted, reconstructed or synthetic source origin")
    frozen_time = immutable_array(time, dtype=float, name="sensor time")
    frozen_actual = immutable_array(actual, dtype=float, name="true concentration")
    indicated = immutable_array(
        _first_order_indication(config, frozen_time, frozen_actual, initial),
        dtype=float, name="indicated concentration",
    )
    content = _sensor_digest(config, frozen_time, frozen_actual, indicated,
                             initial, source_id, mode_id, selected_episode_id,
                             source_origin)
    token = object()
    _PENDING_SENSOR_ISSUERS.add(token)
    try:
        return FirstOrderConcentrationSensorTrace(
            config, frozen_time, frozen_actual, indicated, initial, source_id,
            mode_id, selected_episode_id, source_origin, content, token,
        )
    except Exception:
        _PENDING_SENSOR_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmConfig:
    """Caller-qualified concentration thresholds and discrete confirmation rule."""

    detector_id: str
    location_id: str
    clock_id: str
    operating_mode_id: str
    episode_id: str
    concentration_basis: str
    concentration_unit: str
    trip_threshold: float
    reset_threshold: float
    trip_confirmation_samples: int
    reset_confirmation_samples: int
    maximum_sample_gap_s: float
    sensor_evidence_id: str
    threshold_evidence_id: str
    logic_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in (
            "detector_id", "location_id", "clock_id", "operating_mode_id",
            "episode_id", "concentration_basis", "concentration_unit",
            "sensor_evidence_id", "threshold_evidence_id", "logic_evidence_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        trip = finite(self.trip_threshold, "trip concentration")
        reset = finite(self.reset_threshold, "reset concentration")
        if reset < 0 or trip <= reset:
            raise ValueError("Trip threshold must exceed the reset threshold")
        object.__setattr__(self, "trip_threshold", trip)
        object.__setattr__(self, "reset_threshold", reset)
        for name in ("trip_confirmation_samples", "reset_confirmation_samples"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer sample count")
        gap = finite(self.maximum_sample_gap_s, "maximum sample gap", positive=True)
        object.__setattr__(self, "maximum_sample_gap_s", gap)
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("Declare measured, predicted, reconstructed or synthetic provenance")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmTransition:
    """A trip or reset confirmed at a sampled instant, without interpolation."""

    alarm_active: bool
    first_qualifying_index: int
    confirmation_index: int
    first_qualifying_time_s: float
    confirmation_time_s: float
    first_qualifying_concentration: float
    confirmation_concentration: float


def _simulate(config, time_s, concentration):
    if time_s.ndim != 1 or concentration.shape != time_s.shape or not len(time_s):
        raise ValueError("Time and concentration must be aligned nonempty vectors")
    if (not np.all(np.isfinite(time_s)) or not np.all(np.isfinite(concentration))
            or np.any(time_s < 0) or np.any(concentration < 0)):
        raise ValueError("Clock and concentration samples must be finite and nonnegative")
    if len(time_s) > 1:
        increments = np.diff(time_s)
        if np.any(increments <= 0):
            raise ValueError("Sample times must increase strictly")
        if np.any(increments > config.maximum_sample_gap_s):
            raise ValueError("A sample gap exceeds the declared detector observation limit")

    latched = np.zeros(len(time_s), dtype=bool)
    transitions = []
    active = False
    candidate_start = None
    candidate_count = 0
    required = config.trip_confirmation_samples
    for i, value in enumerate(concentration):
        qualifies = value >= config.trip_threshold if not active else value <= config.reset_threshold
        if qualifies:
            if candidate_start is None:
                candidate_start = i
                candidate_count = 0
            candidate_count += 1
            if candidate_count >= required:
                active = not active
                start = candidate_start
                transitions.append(ConcentrationAlarmTransition(
                    active,
                    start,
                    i,
                    float(time_s[start]),
                    float(time_s[i]),
                    float(concentration[start]),
                    float(value),
                ))
                candidate_start = None
                candidate_count = 0
                required = (config.reset_confirmation_samples if active
                            else config.trip_confirmation_samples)
        else:
            candidate_start = None
            candidate_count = 0
        latched[i] = active
    return latched, tuple(transitions)


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmTrace:
    config: ConcentrationAlarmConfig
    time_s: np.ndarray
    concentration: np.ndarray
    latched_alarm: np.ndarray
    transitions: tuple[ConcentrationAlarmTransition, ...]
    _digest: str = field(repr=False)
    _token: object = field(repr=False)
    sensor_response: FirstOrderConcentrationSensorTrace | None = None
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        _consume_issuer(self._token, _PENDING_TRACE_ISSUERS, "an alarm trace")
        object.__setattr__(self, "time_s", immutable_array(self.time_s, dtype=float, name="time_s"))
        object.__setattr__(self, "concentration", immutable_array(
            self.concentration, dtype=float, name="concentration"
        ))
        object.__setattr__(self, "latched_alarm", immutable_array(
            self.latched_alarm, dtype=bool, name="latched_alarm"
        ))
        object.__setattr__(self, "transitions", tuple(self.transitions))
        if self.sensor_response is not None:
            _require_sensor_alignment(self.config, self.time_s, self.concentration,
                                      self.sensor_response)
        object.__setattr__(self, "_issued_token", self._token)

    def require_current(self):
        if self._token is not self._issued_token:
            raise ValueError("Alarm trace was not issued by the evaluator")
        if self.sensor_response is not None:
            _require_sensor_alignment(self.config, self.time_s, self.concentration,
                                      self.sensor_response)
        expected_state, expected_events = _simulate(self.config, self.time_s, self.concentration)
        if (not np.array_equal(self.latched_alarm, expected_state)
                or self.transitions != expected_events
                or _digest(self.config, self.time_s, self.concentration,
                           self.latched_alarm, self.transitions,
                           self.sensor_response) != self._digest):
            raise ValueError("Concentration alarm trace changed after evaluation")
        return self


def _evaluate_alarm(config, *, time_s, concentration, sensor_response=None):
    if type(config) is not ConcentrationAlarmConfig:
        raise TypeError("Supply an explicit ConcentrationAlarmConfig")
    if sensor_response is not None:
        _require_sensor_alignment(config, time_s, concentration, sensor_response)
    try:
        raw_time = np.asarray(time_s)
        raw_values = np.asarray(concentration)
        if raw_time.dtype.kind not in "iuf" or raw_values.dtype.kind not in "iuf":
            raise ValueError("Time and concentration require real numeric samples")
        time = np.asarray(raw_time, dtype=float)
        values = np.asarray(raw_values, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("Time and concentration require real numeric samples") from error
    state, transitions = _simulate(config, time, values)
    frozen_time = immutable_array(time, dtype=float, name="time_s")
    frozen_values = immutable_array(values, dtype=float, name="concentration")
    frozen_state = immutable_array(state, dtype=bool, name="latched_alarm")
    content = _digest(config, frozen_time, frozen_values, frozen_state, transitions,
                      sensor_response)
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    try:
        return ConcentrationAlarmTrace(
            config, frozen_time, frozen_values, frozen_state, transitions,
            content, token, sensor_response,
        )
    except Exception:
        _PENDING_TRACE_ISSUERS.discard(token)
        raise


def _require_sensor_alignment(config, time_s, concentration, sensor_response):
    if type(sensor_response) is not FirstOrderConcentrationSensorTrace:
        raise TypeError("Supply an evaluator-issued first-order sensor response trace")
    sensor_response.require_current()
    sensor = sensor_response.config
    if (config.detector_id != sensor.sensor_id
            or config.location_id != sensor.location_id
            or config.clock_id != sensor.clock_id
            or config.concentration_basis != sensor.concentration_basis
            or config.concentration_unit != sensor.concentration_unit
            or config.sensor_evidence_id != sensor.sensor_evidence_id
            or config.operating_mode_id != sensor_response.operating_mode_id
            or config.episode_id != sensor_response.episode_id
            or config.origin != sensor_response.origin):
        raise ValueError("Alarm configuration does not match the sensor identity, context, basis and origin")
    if (not np.array_equal(np.asarray(time_s), sensor_response.time_s)
            or not np.array_equal(np.asarray(concentration), sensor_response.indicated_concentration)):
        raise ValueError("Alarm inputs must be the exact issued sensor clock and indication")


def evaluate_concentration_alarm_from_sensor(config, sensor_response):
    """Apply sampled alarm logic to the exact indication of an issued sensor trace."""
    if type(sensor_response) is not FirstOrderConcentrationSensorTrace:
        raise TypeError("Supply an evaluator-issued first-order sensor response trace")
    sensor_response.require_current()
    return _evaluate_alarm(
        config, time_s=sensor_response.time_s,
        concentration=sensor_response.indicated_concentration,
        sensor_response=sensor_response,
    )


def evaluate_concentration_alarm(config, *, time_s, concentration):
    """Apply sampled high-trip/low-reset logic to caller-provided concentration.

    Values use one declared basis/unit throughout. Confirmation is registered at
    the sample that completes the required consecutive count. No crossing time,
    detector dynamics, missing-data behavior, or setpoint is inferred.
    """
    return _evaluate_alarm(config, time_s=time_s, concentration=concentration)


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmEvidence:
    """A source-bound confirmed trip usable by the existing protection replay."""

    trace: ConcentrationAlarmTrace
    transition: ConcentrationAlarmTransition
    clock_id: str
    time_s: float
    observed_mode_id: str
    episode_id: str
    sensor_evidence_ids: Mapping[str, str]
    decision_evidence_id: str
    _content: str = field(repr=False)
    _token: object = field(repr=False)
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        _consume_issuer(self._token, _PENDING_EVENT_ISSUERS, "alarm evidence")
        object.__setattr__(self, "sensor_evidence_ids", MappingProxyType(dict(self.sensor_evidence_ids)))
        object.__setattr__(self, "_issued_token", self._token)

    @classmethod
    def bind(cls, trace, transition):
        if type(trace) is not ConcentrationAlarmTrace:
            raise TypeError("Bind an original concentration alarm trace")
        trace.require_current()
        if (not any(item is transition for item in trace.transitions)
                or type(transition) is not ConcentrationAlarmTransition
                or transition.alarm_active is not True):
            raise ValueError("Protection replay requires an original confirmed trip transition")
        config = trace.config
        content = _digest(config, trace.time_s, trace.concentration,
                          trace.latched_alarm, trace.transitions)
        token = object()
        _PENDING_EVENT_ISSUERS.add(token)
        try:
            return cls(
                trace, transition, config.clock_id, transition.confirmation_time_s,
                config.operating_mode_id, config.episode_id,
                {config.detector_id: config.sensor_evidence_id},
                config.logic_evidence_id, content, token,
            )
        except Exception:
            _PENDING_EVENT_ISSUERS.discard(token)
            raise

    def require_current(self):
        self.trace.require_current()
        if (self._token is not self._issued_token
                or not any(item is self.transition for item in self.trace.transitions)
                or not self.transition.alarm_active
                or self.clock_id != self.trace.config.clock_id
                or self.time_s != self.transition.confirmation_time_s
                or self.observed_mode_id != self.trace.config.operating_mode_id
                or self.episode_id != self.trace.config.episode_id
                or dict(self.sensor_evidence_ids) != {
                    self.trace.config.detector_id: self.trace.config.sensor_evidence_id
                }
                or self.decision_evidence_id != self.trace.config.logic_evidence_id
                or self._content != _digest(
                    self.trace.config, self.trace.time_s, self.trace.concentration,
                    self.trace.latched_alarm, self.trace.transitions
                )):
            raise ValueError("Concentration alarm evidence no longer matches its original trip")
        return self


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmVoteTransition:
    """A sampled change in an explicit k-of-n combination of detector latches."""

    alarm_active: bool
    sample_index: int
    time_s: float
    active_detector_ids: tuple[str, ...]


def _voting_digest(voting_id, logic_evidence_id, votes_required, traces,
                   time_s, vote_count, latched, transitions):
    digest = hashlib.sha256(repr((voting_id, logic_evidence_id, votes_required,
                                 tuple(trace.config.detector_id for trace in traces),
                                 tuple(trace._digest for trace in traces))).encode("utf-8"))
    for array in (time_s, vote_count, latched):
        contiguous = np.ascontiguousarray(array)
        digest.update(contiguous.dtype.str.encode("ascii"))
        digest.update(repr(contiguous.shape).encode("ascii"))
        digest.update(contiguous.tobytes())
    digest.update(repr(transitions).encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmVotingTrace:
    """Same-clock sampled k-of-n vote over original, individually latched alarms."""

    voting_id: str
    logic_evidence_id: str
    votes_required: int
    traces: tuple[ConcentrationAlarmTrace, ...]
    time_s: np.ndarray
    vote_count: np.ndarray
    latched_alarm: np.ndarray
    transitions: tuple[ConcentrationAlarmVoteTransition, ...]
    _digest: str = field(repr=False)
    _token: object = field(repr=False)
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        _consume_issuer(self._token, _PENDING_TRACE_ISSUERS, "a voted alarm trace")
        object.__setattr__(self, "traces", tuple(self.traces))
        object.__setattr__(self, "time_s", immutable_array(self.time_s, dtype=float,
                                                            name="voting time_s"))
        object.__setattr__(self, "vote_count", immutable_array(self.vote_count, dtype=int,
                                                                name="vote_count"))
        object.__setattr__(self, "latched_alarm", immutable_array(self.latched_alarm,
                                                                   dtype=bool,
                                                                   name="voted_alarm"))
        object.__setattr__(self, "transitions", tuple(self.transitions))
        object.__setattr__(self, "_issued_token", self._token)

    @property
    def clock_id(self):
        return self.traces[0].config.clock_id

    @property
    def operating_mode_id(self):
        return self.traces[0].config.operating_mode_id

    @property
    def episode_id(self):
        return self.traces[0].config.episode_id

    @property
    def detector_evidence_ids(self):
        return MappingProxyType({trace.config.detector_id: trace.config.sensor_evidence_id
                                 for trace in self.traces})

    def require_current(self):
        if self._token is not self._issued_token:
            raise ValueError("Voted alarm trace was not retained from its evaluator issuance")
        for trace in self.traces:
            trace.require_current()
        _validate_voting_members(self.traces, self.votes_required)
        times = self.traces[0].time_s
        counts = np.sum(np.stack([trace.latched_alarm for trace in self.traces]), axis=0)
        alarm = counts >= self.votes_required
        expected = []
        prior = False
        for index, active in enumerate(alarm):
            current = bool(active)
            if current != prior:
                detector_ids = tuple(trace.config.detector_id for trace in self.traces
                                     if trace.latched_alarm[index])
                expected.append(ConcentrationAlarmVoteTransition(
                    current, index, float(times[index]), detector_ids,
                ))
            prior = current
        if (not np.array_equal(self.time_s, times)
                or not np.array_equal(self.vote_count, counts)
                or not np.array_equal(self.latched_alarm, alarm)
                or self.transitions != tuple(expected)
                or _voting_digest(self.voting_id, self.logic_evidence_id,
                                  self.votes_required, self.traces, self.time_s,
                                  self.vote_count, self.latched_alarm,
                                  self.transitions) != self._digest):
            raise ValueError("Voted alarm no longer matches its original detector traces")
        return self


def _validate_voting_members(traces, votes_required):
    if type(traces) is not tuple or len(traces) < 2:
        raise ValueError("Detector voting needs at least two original alarm traces")
    if type(votes_required) is not int or not 1 <= votes_required <= len(traces):
        raise ValueError("votes_required must be an integer from one through detector count")
    if any(type(trace) is not ConcentrationAlarmTrace for trace in traces):
        raise TypeError("Voting inputs must be original ConcentrationAlarmTrace objects")
    for trace in traces:
        trace.require_current()
    configs = tuple(trace.config for trace in traces)
    if len({config.detector_id for config in configs}) != len(configs):
        raise ValueError("Detector identities in a voting group must be unique")
    first = configs[0]
    if any((config.clock_id, config.operating_mode_id, config.episode_id)
           != (first.clock_id, first.operating_mode_id, first.episode_id)
           for config in configs[1:]):
        raise ValueError("Voting members must share one clock, operating mode, and episode")
    if any(not np.array_equal(trace.time_s, traces[0].time_s) for trace in traces[1:]):
        raise ValueError("Voting members must have exactly aligned sampled time grids")


def evaluate_concentration_alarm_voting(traces, *, votes_required, voting_id,
                                        logic_evidence_id):
    """Combine already latched detector traces with an explicit same-sample k-of-n rule.

    Individual concentration bases, limits, hysteresis and confirmation rules remain
    detector-owned. This layer adds no independence, common-cause, reliability, missing
    data, asynchronous sampling, voting delay, or setpoint assumptions.
    """
    members = tuple(traces)
    voting = _text(voting_id, "voting identity")
    evidence = _text(logic_evidence_id, "voting logic evidence")
    _validate_voting_members(members, votes_required)
    time = members[0].time_s
    counts = np.sum(np.stack([trace.latched_alarm for trace in members]), axis=0)
    alarm = counts >= votes_required
    transitions = []
    prior = False
    for index, active in enumerate(alarm):
        current = bool(active)
        if current != prior:
            detector_ids = tuple(trace.config.detector_id for trace in members
                                 if trace.latched_alarm[index])
            transitions.append(ConcentrationAlarmVoteTransition(
                current, index, float(time[index]), detector_ids,
            ))
        prior = current
    frozen_time = immutable_array(time, dtype=float, name="voting time_s")
    frozen_count = immutable_array(counts, dtype=int, name="vote_count")
    frozen_alarm = immutable_array(alarm, dtype=bool, name="voted_alarm")
    transition_tuple = tuple(transitions)
    content = _voting_digest(voting, evidence, votes_required, members,
                             frozen_time, frozen_count, frozen_alarm, transition_tuple)
    token = object()
    _PENDING_TRACE_ISSUERS.add(token)
    try:
        return ConcentrationAlarmVotingTrace(
            voting, evidence, votes_required, members, frozen_time, frozen_count,
            frozen_alarm, transition_tuple, content, token,
        )
    except Exception:
        _PENDING_TRACE_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class ConcentrationAlarmVotingEvidence:
    """Evidence for an original rising k-of-n transition passed to protection replay."""

    trace: ConcentrationAlarmVotingTrace
    transition: ConcentrationAlarmVoteTransition
    clock_id: str
    time_s: float
    observed_mode_id: str
    episode_id: str
    sensor_evidence_ids: Mapping[str, str]
    decision_evidence_id: str
    _content: str = field(repr=False)
    _token: object = field(repr=False)
    _issued_token: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        _consume_issuer(self._token, _PENDING_EVENT_ISSUERS, "voted alarm evidence")
        object.__setattr__(self, "sensor_evidence_ids",
                           MappingProxyType(dict(self.sensor_evidence_ids)))
        object.__setattr__(self, "_issued_token", self._token)

    @classmethod
    def bind(cls, trace, transition):
        if type(trace) is not ConcentrationAlarmVotingTrace:
            raise TypeError("Bind an original concentration alarm voting trace")
        trace.require_current()
        if (not any(item is transition for item in trace.transitions)
                or type(transition) is not ConcentrationAlarmVoteTransition
                or transition.alarm_active is not True):
            raise ValueError("Protection replay requires an original confirmed voted trip")
        content = _voting_digest(trace.voting_id, trace.logic_evidence_id,
                                 trace.votes_required, trace.traces, trace.time_s,
                                 trace.vote_count, trace.latched_alarm, trace.transitions)
        token = object()
        _PENDING_EVENT_ISSUERS.add(token)
        try:
            return cls(trace, transition, trace.clock_id, transition.time_s,
                       trace.operating_mode_id, trace.episode_id,
                       dict(trace.detector_evidence_ids), trace.logic_evidence_id,
                       content, token)
        except Exception:
            _PENDING_EVENT_ISSUERS.discard(token)
            raise

    def require_current(self):
        self.trace.require_current()
        if (self._token is not self._issued_token
                or not any(item is self.transition for item in self.trace.transitions)
                or self.transition.alarm_active is not True
                or self.clock_id != self.trace.clock_id
                or self.time_s != self.transition.time_s
                or self.observed_mode_id != self.trace.operating_mode_id
                or self.episode_id != self.trace.episode_id
                or dict(self.sensor_evidence_ids) != dict(self.trace.detector_evidence_ids)
                or self.decision_evidence_id != self.trace.logic_evidence_id
                or self._content != _voting_digest(
                    self.trace.voting_id, self.trace.logic_evidence_id,
                    self.trace.votes_required, self.trace.traces, self.trace.time_s,
                    self.trace.vote_count, self.trace.latched_alarm,
                    self.trace.transitions)):
            raise ValueError("Voted alarm evidence no longer matches its detector traces")
        return self
