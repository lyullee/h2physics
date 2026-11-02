"""Explicit observation operators for isothermal pipe-wave traces.

These types accept caller-owned measured histories. They do not read files,
infer source metadata, estimate EOS parameters, or qualify a pipeline model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core import finite, immutable_array
from ..isothermal_pipe_waves import IsothermalPipeWaveTrace


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty identity")
    return value.strip()


def _observation_arrays(time_s, values, uncertainty, *, value_name: str):
    time = immutable_array(time_s, dtype=float, name="time_s")
    value = immutable_array(values, dtype=float, name=value_name)
    sigma = immutable_array(uncertainty, dtype=float, name=f"{value_name}_uncertainty")
    if (time.ndim != 1 or len(time) < 2 or value.shape != time.shape
            or sigma.shape != time.shape):
        raise ValueError("Observation time, value and uncertainty arrays must be aligned vectors")
    if (not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0.)
            or not np.all(np.isfinite(value)) or not np.all(np.isfinite(sigma))
            or np.any(sigma <= 0.)):
        raise ValueError("Observation arrays need increasing finite times, finite values and positive uncertainty")
    return time, value, sigma


@dataclass(frozen=True, slots=True)
class PipelinePressureHistory:
    """One absolute-pressure channel at a declared axial tap.

    Values and standard uncertainties are Pa. Time must already use the
    caller-declared common clock; no offset or unit conversion is inferred.
    """

    time_s: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    standard_uncertainty_pa: np.ndarray = field(repr=False, compare=False)
    tap_position_m: float
    channel_id: str
    clock_id: str
    source_evidence_id: str
    sensor_mapping_evidence_id: str
    pressure_basis: str = "absolute"

    def __post_init__(self):
        time, pressure, sigma = _observation_arrays(
            self.time_s, self.pressure_pa, self.standard_uncertainty_pa,
            value_name="pressure_pa",
        )
        if np.any(pressure <= 0.):
            raise ValueError("Absolute pressure observations must be positive")
        position = finite(self.tap_position_m, "tap_position_m")
        if position < 0.:
            raise ValueError("tap_position_m cannot be negative")
        if self.pressure_basis != "absolute":
            raise ValueError("Only absolute pressure observations in Pa are admitted")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "standard_uncertainty_pa", sigma)
        object.__setattr__(self, "tap_position_m", position)
        object.__setattr__(self, "channel_id", _identifier(self.channel_id, "channel_id"))
        object.__setattr__(self, "clock_id", _identifier(self.clock_id, "clock_id"))
        object.__setattr__(self, "source_evidence_id",
                           _identifier(self.source_evidence_id, "source_evidence_id"))
        object.__setattr__(self, "sensor_mapping_evidence_id",
                           _identifier(self.sensor_mapping_evidence_id,
                                       "sensor_mapping_evidence_id"))


@dataclass(frozen=True, slots=True)
class PipelineMassFlowHistory:
    """One mass-flow channel in kg/s, positive toward increasing pipe x."""

    time_s: np.ndarray = field(repr=False, compare=False)
    mass_flow_kg_s: np.ndarray = field(repr=False, compare=False)
    standard_uncertainty_kg_s: np.ndarray = field(repr=False, compare=False)
    meter_position_m: float
    channel_id: str
    clock_id: str
    source_evidence_id: str
    sensor_mapping_evidence_id: str
    positive_direction: str = "toward_increasing_x"

    def __post_init__(self):
        time, flow, sigma = _observation_arrays(
            self.time_s, self.mass_flow_kg_s, self.standard_uncertainty_kg_s,
            value_name="mass_flow_kg_s",
        )
        position = finite(self.meter_position_m, "meter_position_m")
        if position < 0.:
            raise ValueError("meter_position_m cannot be negative")
        if self.positive_direction != "toward_increasing_x":
            raise ValueError("Flow sign must be declared positive toward increasing pipe x")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "mass_flow_kg_s", flow)
        object.__setattr__(self, "standard_uncertainty_kg_s", sigma)
        object.__setattr__(self, "meter_position_m", position)
        object.__setattr__(self, "channel_id", _identifier(self.channel_id, "channel_id"))
        object.__setattr__(self, "clock_id", _identifier(self.clock_id, "clock_id"))
        object.__setattr__(self, "source_evidence_id",
                           _identifier(self.source_evidence_id, "source_evidence_id"))
        object.__setattr__(self, "sensor_mapping_evidence_id",
                           _identifier(self.sensor_mapping_evidence_id,
                                       "sensor_mapping_evidence_id"))


@dataclass(frozen=True, slots=True)
class IsothermalPipeObservationComparison:
    """Residuals from an explicit, no-time-interpolation observation mapping."""

    pressure_observation: PipelinePressureHistory = field(repr=False, compare=False)
    flow_observation: PipelineMassFlowHistory = field(repr=False, compare=False)
    trace: IsothermalPipeWaveTrace = field(repr=False, compare=False)
    model_clock_id: str
    clock_alignment_evidence_id: str
    pressure_model_pa: np.ndarray = field(repr=False, compare=False)
    pressure_residual_pa: np.ndarray = field(repr=False, compare=False)
    flow_model_kg_s: np.ndarray = field(repr=False, compare=False)
    flow_residual_kg_s: np.ndarray = field(repr=False, compare=False)

    def __post_init__(self):
        model_clock = _identifier(self.model_clock_id, "model_clock_id")
        alignment = _identifier(self.clock_alignment_evidence_id,
                                "clock_alignment_evidence_id")
        arrays = (
            ("pressure_model_pa", self.pressure_model_pa,
             self.pressure_observation.time_s.shape),
            ("pressure_residual_pa", self.pressure_residual_pa,
             self.pressure_observation.time_s.shape),
            ("flow_model_kg_s", self.flow_model_kg_s,
             self.flow_observation.time_s.shape),
            ("flow_residual_kg_s", self.flow_residual_kg_s,
             self.flow_observation.time_s.shape),
        )
        for name, values, shape in arrays:
            array = immutable_array(values, dtype=float, name=name)
            if array.shape != shape or not np.all(np.isfinite(array)):
                raise ValueError(f"{name} must be a finite vector aligned with its observation")
            object.__setattr__(self, name, array)
        if (self.pressure_observation.clock_id != model_clock
                or self.flow_observation.clock_id != model_clock):
            raise ValueError("Model and observation clocks must share the declared clock identity")
        pressure_indices = _exact_trace_indices(
            self.trace, self.pressure_observation.time_s,
            channel_id=self.pressure_observation.channel_id,
        )
        flow_indices = _exact_trace_indices(
            self.trace, self.flow_observation.time_s,
            channel_id=self.flow_observation.channel_id,
        )
        centers = self.trace.cell_center_m
        dx = float(np.diff(centers)[0])
        if not np.allclose(np.diff(centers), dx, rtol=1e-12, atol=0.):
            raise ValueError("Observation mapping requires the solver's uniform axial grid")
        faces = np.concatenate(([centers[0] - .5 * dx], centers + .5 * dx))
        if (self.pressure_observation.tap_position_m < centers[0]
                or self.pressure_observation.tap_position_m > centers[-1]
                or self.flow_observation.meter_position_m < faces[0]
                or self.flow_observation.meter_position_m > faces[-1]):
            raise ValueError("Sensor location lies outside the represented pipe support")
        pressure_expected = np.asarray([
            np.interp(self.pressure_observation.tap_position_m, centers,
                      self.trace.pressure_pa[index])
            for index in pressure_indices
        ])
        flow_expected = np.asarray([
            np.interp(self.flow_observation.meter_position_m, faces,
                      self.trace.face_mass_flow_kg_s[index])
            for index in flow_indices
        ])
        if (not np.array_equal(self.pressure_model_pa, pressure_expected)
                or not np.array_equal(
                    self.pressure_residual_pa,
                    pressure_expected - self.pressure_observation.pressure_pa,
                )
                or not np.array_equal(self.flow_model_kg_s, flow_expected)
                or not np.array_equal(
                    self.flow_residual_kg_s,
                    flow_expected - self.flow_observation.mass_flow_kg_s,
                )):
            raise ValueError("Comparison arrays do not match the retained trace and observations")
        object.__setattr__(self, "model_clock_id", model_clock)
        object.__setattr__(self, "clock_alignment_evidence_id", alignment)

    @property
    def pressure_weighted_rms(self) -> float:
        normalized = (self.pressure_residual_pa
                      / self.pressure_observation.standard_uncertainty_pa)
        return float(np.sqrt(np.mean(normalized**2)))

    @property
    def flow_weighted_rms(self) -> float:
        normalized = (self.flow_residual_kg_s
                      / self.flow_observation.standard_uncertainty_kg_s)
        return float(np.sqrt(np.mean(normalized**2)))


def _exact_trace_indices(trace: IsothermalPipeWaveTrace, times, *, channel_id: str):
    indices = np.searchsorted(trace.time_s, times)
    in_bounds = indices < len(trace.time_s)
    if (not np.all(in_bounds)
            or not np.array_equal(trace.time_s[indices], times)):
        raise ValueError(
            f"{channel_id} times must be exact samples in the model trace; "
            "temporal interpolation is not implicit"
        )
    return indices


def compare_isothermal_pipe_observations(
    trace: IsothermalPipeWaveTrace,
    pressure: PipelinePressureHistory,
    mass_flow: PipelineMassFlowHistory,
    *,
    model_clock_id: str,
    clock_alignment_evidence_id: str,
) -> IsothermalPipeObservationComparison:
    """Compare measured channels with one native pipe-wave trace.

    Pressure and flow are linearly interpolated in space between retained
    native cell-centre/face values, with no spatial extrapolation. Observation
    times must exactly occur in the trace; no temporal interpolation or clock
    shifting is performed. The result is diagnostic and cannot qualify a model.
    """
    if type(trace) is not IsothermalPipeWaveTrace:
        raise TypeError("trace must be an IsothermalPipeWaveTrace")
    if type(pressure) is not PipelinePressureHistory:
        raise TypeError("pressure must be a PipelinePressureHistory")
    if type(mass_flow) is not PipelineMassFlowHistory:
        raise TypeError("mass_flow must be a PipelineMassFlowHistory")
    model_clock = _identifier(model_clock_id, "model_clock_id")
    _identifier(clock_alignment_evidence_id, "clock_alignment_evidence_id")
    if pressure.clock_id != model_clock or mass_flow.clock_id != model_clock:
        raise ValueError("Pressure, flow and model must use the same declared clock")

    pressure_indices = _exact_trace_indices(
        trace, pressure.time_s, channel_id=pressure.channel_id,
    )
    flow_indices = _exact_trace_indices(
        trace, mass_flow.time_s, channel_id=mass_flow.channel_id,
    )
    centers = trace.cell_center_m
    if pressure.tap_position_m < centers[0] or pressure.tap_position_m > centers[-1]:
        raise ValueError("Pressure tap lies outside the represented cell-centre range")
    dx = float(np.diff(centers)[0])
    if not np.allclose(np.diff(centers), dx, rtol=1e-12, atol=0.):
        raise ValueError("Observation mapping requires the solver's uniform axial grid")
    face_positions = np.concatenate((
        [centers[0] - 0.5 * dx], centers + 0.5 * dx,
    ))
    if (mass_flow.meter_position_m < face_positions[0]
            or mass_flow.meter_position_m > face_positions[-1]):
        raise ValueError("Mass-flow meter lies outside the represented pipe faces")
    model_pressure = np.asarray([
        np.interp(pressure.tap_position_m, centers, trace.pressure_pa[index])
        for index in pressure_indices
    ])
    model_flow = np.asarray([
        np.interp(mass_flow.meter_position_m, face_positions,
                  trace.face_mass_flow_kg_s[index])
        for index in flow_indices
    ])
    return IsothermalPipeObservationComparison(
        pressure_observation=pressure,
        flow_observation=mass_flow,
        trace=trace,
        model_clock_id=model_clock,
        clock_alignment_evidence_id=clock_alignment_evidence_id,
        pressure_model_pa=model_pressure,
        pressure_residual_pa=model_pressure - pressure.pressure_pa,
        flow_model_kg_s=model_flow,
        flow_residual_kg_s=model_flow - mass_flow.mass_flow_kg_s,
    )
