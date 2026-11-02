"""Explicit differential-pressure histories for transient mechanical loads.

A pressure curve indexed by hypothetical ignition delay is a different object
and is intentionally not accepted here. Values describe one actual load event.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid

from .core import _real_numeric_array, immutable_array


@dataclass(frozen=True, slots=True)
class PressureTimeHistory:
    """Piecewise-linear applied pressure in Pa on an identified event clock.

    Pressure is the net pressure difference across the loaded surface; positive
    acts in the selected displacement direction. It is zero outside the sampled
    support. Nonzero endpoints therefore declare instantaneous load jumps.
    Reflection and spatial-to-generalized-load factors belong to the supplier.
    """

    time_s: np.ndarray
    differential_pressure_pa: np.ndarray
    clock_id: str
    load_id: str
    evidence_id: str

    def __post_init__(self):
        time = _real_numeric_array(self.time_s, "load time")
        pressure = _real_numeric_array(self.differential_pressure_pa, "load pressure")
        if (time.ndim != 1 or len(time) < 2 or pressure.shape != time.shape
                or not np.all(np.isfinite(time)) or not np.all(np.isfinite(pressure))
                or time[0] < 0 or np.any(np.diff(time) <= 0)):
            raise ValueError("Supply finite matching pressure/time vectors with increasing time >= 0")
        for name in ("clock_id", "load_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Load, clock and evidence identities must be explicit")
        object.__setattr__(self, "time_s", immutable_array(time))
        object.__setattr__(self, "differential_pressure_pa", immutable_array(pressure))

    def at(self, time_s):
        """Interpolate on the stated support; no invented pressure tail."""
        time = _real_numeric_array(time_s, "evaluation time")
        if not np.all(np.isfinite(time)):
            raise ValueError("Evaluation times must be finite")
        result = np.interp(time, self.time_s, self.differential_pressure_pa, left=0., right=0.)
        return float(result) if np.ndim(result) == 0 else immutable_array(result)

    @property
    def signed_impulse_pa_s(self):
        return float(trapezoid(self.differential_pressure_pa, self.time_s))
