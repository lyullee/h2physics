"""Caller-owned pressure/time histories for isothermal pipe-wave reservoirs."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .core import Origin, finite, immutable_array


@dataclass(frozen=True, slots=True)
class FiniteReservoirPressureBoundary:
    """A finite, externally modeled reservoir's prescribed pressure history.

    This object carries an explicit pressure/time state sequence and its owner,
    evidence, clock, EOS and origin. It does not evolve reservoir mass itself.
    The pipe solver consumes the trace without extrapolating beyond its knots.
    """

    identifier: str
    state_owner_id: str
    state_evidence_id: str
    clock_id: str
    eos_identity: str
    temperature_k: float
    time_s: np.ndarray = field(repr=False, compare=False)
    pressure_pa: np.ndarray = field(repr=False, compare=False)
    origin: Origin = Origin.UNRESOLVED

    def __post_init__(self):
        for label, value in (
            ("reservoir identifier", self.identifier),
            ("reservoir state owner", self.state_owner_id),
            ("reservoir state evidence", self.state_evidence_id),
            ("reservoir clock", self.clock_id),
            ("reservoir EOS identity", self.eos_identity),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {label}")
        temperature = finite(self.temperature_k, "reservoir temperature K", positive=True)
        times = immutable_array(self.time_s, dtype=float, name="reservoir time_s")
        pressure = immutable_array(self.pressure_pa, dtype=float, name="reservoir pressure_pa")
        if (times.ndim != 1 or pressure.ndim != 1 or len(times) < 2
                or pressure.shape != times.shape or not np.all(np.isfinite(times))
                or not np.all(np.isfinite(pressure)) or np.any(pressure <= 0.)
                or np.any(np.diff(times) <= 0.)):
            raise ValueError("Reservoir pressure history requires matching increasing times and positive finite pressures")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Resolve or explicitly author the reservoir pressure-state origin")
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "pressure_pa", pressure)
        object.__setattr__(self, "origin", origin)

    def require_compatible(self, *, start_time_s: float, end_time_s: float,
                           clock_id: str, eos_identity: str, temperature_k: float):
        if self.clock_id != clock_id:
            raise ValueError("Reservoir state history uses a different clock")
        if self.eos_identity != eos_identity:
            raise ValueError("Reservoir state history names a different isothermal EOS")
        if self.temperature_k != finite(temperature_k, "pipe temperature K", positive=True):
            raise ValueError("Reservoir and pipe temperatures must match exactly")
        start = finite(start_time_s, "simulation start time")
        end = finite(end_time_s, "simulation end time")
        if self.time_s[0] > start or self.time_s[-1] < end:
            raise ValueError("Reservoir pressure knots must cover the full pipe simulation interval")
        return self

    def pressure_at(self, time_s: float) -> float:
        """Return linearly interpolated pressure without temporal extrapolation."""
        time = finite(time_s, "reservoir query time")
        if time < self.time_s[0] or time > self.time_s[-1]:
            raise ValueError("Reservoir pressure query lies outside its declared time support")
        right = int(np.searchsorted(self.time_s, time, side="left"))
        if right < len(self.time_s) and self.time_s[right] == time:
            return float(self.pressure_pa[right])
        left = right - 1
        fraction = (time - self.time_s[left]) / (self.time_s[right] - self.time_s[left])
        return float(self.pressure_pa[left] + fraction * (
            self.pressure_pa[right] - self.pressure_pa[left]
        ))


__all__ = ["FiniteReservoirPressureBoundary"]
