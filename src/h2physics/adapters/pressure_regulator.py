"""Sampled PI pressure regulation commands for an existing finite-stroke valve.

This module supplies a caller-parameterized control law. Flow remains owned by
the shared valve/nozzle model and pressure evolution remains owned by the
caller’s finite-volume, linepack, or native process model.
"""

from dataclasses import dataclass

from ..core import finite
from .lh2dt_valve_actuator import ValveCommand


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty identity")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PressureRegulatorMeasurement:
    """One absolute downstream-pressure sample with caller-owned lineage."""

    time_s: float
    pressure_pa_absolute: float
    sensor_id: str
    sensor_owner_id: str
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        time_s = finite(self.time_s, "time_s")
        if time_s < 0.:
            raise ValueError("Measurement time must be nonnegative")
        pressure = finite(self.pressure_pa_absolute,
                          "pressure_pa_absolute", positive=True)
        object.__setattr__(self, "time_s", time_s)
        object.__setattr__(self, "pressure_pa_absolute", pressure)
        for name in ("sensor_id", "sensor_owner_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _label(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class PressureRegulatorState:
    """Controller memory at one sample boundary."""

    controller_id: str
    time_s: float
    integral_error_normalized_s: float
    sensor_id: str
    sensor_owner_id: str
    clock_id: str

    def __post_init__(self):
        for name in ("controller_id", "sensor_id", "sensor_owner_id", "clock_id"):
            object.__setattr__(self, name, _label(getattr(self, name), name))
        time_s = finite(self.time_s, "time_s")
        if time_s < 0.:
            raise ValueError("Controller time must be nonnegative")
        object.__setattr__(self, "time_s", time_s)
        finite(self.integral_error_normalized_s,
               "integral_error_normalized_s")


@dataclass(frozen=True, slots=True)
class PressureRegulatorOutput:
    """One pressure sample, command interval, and resulting PI memory."""

    measurement: PressureRegulatorMeasurement
    command: ValveCommand
    next_state: PressureRegulatorState
    normalized_error: float
    unconstrained_target_stroke: float
    saturated: bool
    controller_evidence_id: str

    def __post_init__(self):
        if type(self.measurement) is not PressureRegulatorMeasurement:
            raise TypeError("Output requires its typed pressure measurement")
        if type(self.command) is not ValveCommand:
            raise TypeError("Output must contain the valve actuator's ValveCommand")
        if type(self.next_state) is not PressureRegulatorState:
            raise TypeError("Output requires the resulting controller state")
        finite(self.normalized_error, "normalized_error")
        finite(self.unconstrained_target_stroke,
               "unconstrained_target_stroke")
        if not isinstance(self.saturated, bool):
            raise TypeError("saturated must be bool")
        object.__setattr__(self, "controller_evidence_id",
                           _label(self.controller_evidence_id,
                                  "controller_evidence_id"))
        if (self.command.start_s != self.measurement.time_s
                or self.command.end_s != self.next_state.time_s
                or not self.next_state.controller_id.strip()
                or self.next_state.sensor_id != self.measurement.sensor_id
                or self.next_state.sensor_owner_id != self.measurement.sensor_owner_id
                or self.next_state.clock_id != self.measurement.clock_id):
            raise ValueError("Controller output interval or measurement lineage is inconsistent")


@dataclass(frozen=True, slots=True)
class ProportionalIntegralPressureRegulator:
    """Caller-tuned sampled PI controller for downstream absolute pressure.

    Gains act on pressure error divided by ``pressure_scale_pa``. The output is
    an absolute target stroke fraction in the caller's admitted stroke window;
    the existing finite-stroke actuator applies its opening/closing rates.
    Saturation uses conditional integration anti-windup. No setpoint, sensor,
    tuning, valve map, or process pressure response is inferred.
    """

    controller_id: str
    setpoint_pa_absolute: float
    pressure_scale_pa: float
    proportional_gain: float
    integral_gain_s_inv: float
    bias_stroke_fraction: float
    minimum_target_stroke_fraction: float
    maximum_target_stroke_fraction: float
    maximum_integral_error_normalized_s: float
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        for name in ("controller_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _label(getattr(self, name), name))
        object.__setattr__(self, "setpoint_pa_absolute",
                           finite(self.setpoint_pa_absolute,
                                  "setpoint_pa_absolute", positive=True))
        object.__setattr__(self, "pressure_scale_pa",
                           finite(self.pressure_scale_pa,
                                  "pressure_scale_pa", positive=True))
        for name in ("proportional_gain", "integral_gain_s_inv"):
            value = finite(getattr(self, name), name)
            if value < 0.:
                raise ValueError(f"{name} must be nonnegative")
            object.__setattr__(self, name, value)
        if self.proportional_gain == 0. and self.integral_gain_s_inv == 0.:
            raise ValueError("At least one PI gain must be positive")
        for name in ("bias_stroke_fraction", "minimum_target_stroke_fraction",
                     "maximum_target_stroke_fraction"):
            value = finite(getattr(self, name), name)
            if not 0. <= value <= 1.:
                raise ValueError(f"{name} must lie in [0, 1]")
            object.__setattr__(self, name, value)
        if self.minimum_target_stroke_fraction >= self.maximum_target_stroke_fraction:
            raise ValueError("Target-stroke bounds must be strictly increasing")
        if not (self.minimum_target_stroke_fraction <= self.bias_stroke_fraction
                <= self.maximum_target_stroke_fraction):
            raise ValueError("Bias stroke must lie inside target-stroke bounds")
        object.__setattr__(self, "maximum_integral_error_normalized_s",
                           finite(self.maximum_integral_error_normalized_s,
                                  "maximum_integral_error_normalized_s",
                                  positive=True))

    def initial_state(self, *, time_s: float, sensor_id: str,
                      sensor_owner_id: str) -> PressureRegulatorState:
        """Bind the controller to one sampled sensor, owner, and clock."""
        return PressureRegulatorState(
            controller_id=self.controller_id,
            time_s=time_s,
            integral_error_normalized_s=0.,
            sensor_id=sensor_id,
            sensor_owner_id=sensor_owner_id,
            clock_id=self.clock_id,
        )

    def step(self, state: PressureRegulatorState,
             measurement: PressureRegulatorMeasurement, *,
             end_time_s: float) -> PressureRegulatorOutput:
        """Return one bounded valve target over the next held command interval."""
        if type(state) is not PressureRegulatorState:
            raise TypeError("PI step requires its typed controller state")
        if type(measurement) is not PressureRegulatorMeasurement:
            raise TypeError("PI step requires a typed pressure measurement")
        end_time = finite(end_time_s, "end_time_s", positive=True)
        if state.controller_id != self.controller_id:
            raise ValueError("Controller state belongs to a different regulator")
        if state.clock_id != self.clock_id or measurement.clock_id != self.clock_id:
            raise ValueError("Controller, state and measurement clocks must match")
        if measurement.time_s != state.time_s:
            raise ValueError("Measurement must land exactly on the controller-state time")
        if (measurement.sensor_id != state.sensor_id
                or measurement.sensor_owner_id != state.sensor_owner_id):
            raise ValueError("Measurement source or owner changed during the controller run")
        if end_time <= measurement.time_s:
            raise ValueError("Controller output interval must have positive duration")

        error = ((self.setpoint_pa_absolute - measurement.pressure_pa_absolute)
                 / self.pressure_scale_pa)
        duration = end_time - measurement.time_s
        prior_integral = state.integral_error_normalized_s
        integral_limit = self.maximum_integral_error_normalized_s
        if abs(prior_integral) > integral_limit:
            raise ValueError("Controller integral state exceeds its admitted bound")
        candidate_integral = max(-integral_limit,
                                 min(integral_limit, prior_integral + error * duration))

        def raw_target(integral):
            return (self.bias_stroke_fraction
                    + self.proportional_gain * error
                    + self.integral_gain_s_inv * integral)

        raw = raw_target(candidate_integral)
        low, high = (self.minimum_target_stroke_fraction,
                     self.maximum_target_stroke_fraction)
        if (raw > high and error > 0.) or (raw < low and error < 0.):
            candidate_integral = prior_integral
            raw = raw_target(candidate_integral)
        target = max(low, min(high, raw))
        saturated = target != raw
        next_state = PressureRegulatorState(
            controller_id=self.controller_id,
            time_s=end_time,
            integral_error_normalized_s=candidate_integral,
            sensor_id=state.sensor_id,
            sensor_owner_id=state.sensor_owner_id,
            clock_id=state.clock_id,
        )
        command = ValveCommand(
            start_s=measurement.time_s,
            end_s=end_time,
            target_stroke_fraction=target,
            command_id=f"{self.controller_id}:{measurement.time_s:.12g}",
            mode="operate",
        )
        return PressureRegulatorOutput(
            measurement=measurement,
            command=command,
            next_state=next_state,
            normalized_error=error,
            unconstrained_target_stroke=raw,
            saturated=saturated,
            controller_evidence_id=self.evidence_id,
        )


__all__ = [
    "PressureRegulatorMeasurement",
    "PressureRegulatorOutput",
    "PressureRegulatorState",
    "ProportionalIntegralPressureRegulator",
]
