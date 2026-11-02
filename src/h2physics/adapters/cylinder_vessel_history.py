"""Lossless bridge from sampled cylinder pressure loads to vessel history records.

This adapter maps typed pressure samples into the existing HELPR vessel-history
contract. It does not calculate mechanics, reconstruct missing values, or qualify
the pressure/temperature data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core import immutable_array, Origin
from ..materials.elastic_cylinder import CylinderStressSamples
from .vessel_failure import VesselFailureContext, VesselFailureHistory, VesselLoading


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value


def _finite_vector(value, name: str, *, positive: bool = False) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1 or raw.size < 2 or not np.issubdtype(raw.dtype, np.number):
        raise ValueError(f"{name} must be a numeric one-dimensional series with >=2 points")
    if np.issubdtype(raw.dtype, np.bool_):
        raise ValueError(f"{name} cannot be boolean")
    try:
        result = np.array(raw, dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite numeric series") from exc
    if not np.all(np.isfinite(result)) or (positive and np.any(result <= 0)):
        qualifier = "positive and finite" if positive else "finite"
        raise ValueError(f"{name} must contain only {qualifier} values")
    result = immutable_array(result, name="result")
    return result


@dataclass(frozen=True, slots=True)
class CylinderVesselHistoryBinding:
    """Retain source samples and their mapped vessel history as one binding."""

    pressure_samples: CylinderStressSamples
    history: VesselFailureHistory
    wall_temperature_k: np.ndarray
    phase_id: str
    pressure_source_evidence_id: str
    temperature_evidence_id: str

    def __post_init__(self):
        if type(self.pressure_samples) is not CylinderStressSamples:
            raise TypeError("Retain the original typed cylinder pressure samples")
        if type(self.history) is not VesselFailureHistory:
            raise TypeError("Retain the actual vessel-failure history")
        temperatures = _finite_vector(self.wall_temperature_k, "wall temperature K", positive=True)
        if len(temperatures) != len(self.pressure_samples.time_s):
            raise ValueError("Wall-temperature and pressure histories must have the same samples")
        if len(self.history.samples) != len(self.pressure_samples.time_s):
            raise ValueError("Mapped loading history must preserve all pressure samples")
        _identity(self.phase_id, "single pressure-history phase identity")
        _identity(self.pressure_source_evidence_id, "pressure source evidence identity")
        _identity(self.temperature_evidence_id, "wall-temperature evidence identity")
        context = self.history.context
        if context.clock_id != self.pressure_samples.clock_id:
            raise ValueError("Binding pressure clock and vessel context clock differ")
        if context.source_id != self.pressure_source_evidence_id:
            raise ValueError("Binding source evidence differs from the vessel context")
        if context.wall_temperature_evidence_id != self.temperature_evidence_id:
            raise ValueError("Binding temperature evidence differs from the vessel context")
        if any(load.origin != context.origin for load in self.pressure_samples.loads):
            raise ValueError("Binding pressure origins differ from the vessel context")
        for index, (loading, load, time, temperature) in enumerate(
            zip(
                self.history.samples,
                self.pressure_samples.loads,
                self.pressure_samples.time_s,
                temperatures,
                strict=True,
            )
        ):
            if (
                loading.time_s != time
                or loading.internal_pressure_pa_absolute != load.internal_pressure_pa
                or loading.external_pressure_pa_absolute != load.external_pressure_pa
                or loading.wall_temperature_k != temperature
                or loading.phase_id != self.phase_id
            ):
                raise ValueError(f"Mapped vessel loading {index} differs from retained source data")
        temperatures = immutable_array(temperatures, name="temperatures")
        object.__setattr__(self, "wall_temperature_k", temperatures)


def bind_cylinder_samples_to_vessel_history(
    pressure_samples: CylinderStressSamples,
    context: VesselFailureContext,
    wall_temperature_k,
    *,
    phase_id: str,
    pressure_source_evidence_id: str,
    temperature_evidence_id: str,
    reconstruction_evidence_id: str,
) -> CylinderVesselHistoryBinding:
    """Map pressure/time samples to the existing typed HELPR loading history.

    The wall-temperature vector is caller-supplied, one value per pressure sample.
    All clocks, origins and evidence IDs must agree explicitly. No interpolation,
    phase transition handling, pressure-basis conversion or stress recomputation is
    performed. Pressure samples are retained by the returned binding alongside the
    mapped history so their load identities and Lamé fields remain inspectable.
    """
    if type(pressure_samples) is not CylinderStressSamples:
        raise TypeError("Pass the actual CylinderStressSamples result")
    if type(context) is not VesselFailureContext:
        raise TypeError("Pass the actual VesselFailureContext")
    if pressure_samples.clock_id != context.clock_id:
        raise ValueError("Cylinder pressure and vessel context clock identities differ")
    if any(load.origin is Origin.UNRESOLVED for load in pressure_samples.loads):
        raise ValueError("Unresolved pressure sample origins cannot enter vessel history")
    if any(load.origin != context.origin for load in pressure_samples.loads):
        raise ValueError("Pressure sample origins must match the vessel-history context")
    if not pressure_samples.loads:
        raise ValueError("Pressure samples are required")

    pressure_source_evidence_id = _identity(
        pressure_source_evidence_id, "pressure source evidence identity"
    )
    temperature_evidence_id = _identity(
        temperature_evidence_id, "wall-temperature evidence identity"
    )
    reconstruction_evidence_id = _identity(
        reconstruction_evidence_id, "history reconstruction evidence identity"
    )
    if pressure_source_evidence_id != context.source_id:
        raise ValueError("Pressure source evidence must match the vessel context source")
    if temperature_evidence_id != context.wall_temperature_evidence_id:
        raise ValueError("Temperature evidence must match the vessel context declaration")
    phase_id = _identity(phase_id, "single pressure-history phase identity")

    temperatures = _finite_vector(wall_temperature_k, "wall temperature K", positive=True)
    times = _finite_vector(pressure_samples.time_s, "pressure sample time s")
    if len(temperatures) != len(times) or len(pressure_samples.loads) != len(times):
        raise ValueError("Pressure and wall-temperature series must have matching sample counts")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Pressure sample times must be strictly increasing")

    loadings = []
    for time, load, temperature in zip(times, pressure_samples.loads, temperatures, strict=True):
        if load.external_pressure_pa >= load.internal_pressure_pa:
            raise ValueError(
                "Vessel failure bridge requires inside pressure above outside pressure; "
                "external-pressure buckling is not modeled"
            )
        loadings.append(
            VesselLoading(
                float(time),
                load.internal_pressure_pa,
                load.external_pressure_pa,
                float(temperature),
                phase_id,
            )
        )
    history = VesselFailureHistory(
        context,
        tuple(loadings),
        reconstruction_evidence_id,
    )
    return CylinderVesselHistoryBinding(
        pressure_samples,
        history,
        temperatures,
        phase_id,
        pressure_source_evidence_id,
        temperature_evidence_id,
    )
