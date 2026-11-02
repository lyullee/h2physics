"""Complex small-signal observations and a shared Cartesian fitting projection.

The phasor convention is exp(+j*omega*t); capacitive impedance has negative
imaginary part. Complex components are correlated views of each reading.
"""

from dataclasses import dataclass, field

import numpy as np

from .core import Origin, immutable_array
from .observations import ObservationTable, Variable

FREQUENCY = Variable("frequency_hz", "frequency", "Hz")
COMPONENT = Variable("component", "complex_component_selector", "1")
IMPEDANCE = Variable("impedance_ohm", "impedance_component", "ohm", "whole-cell;exp(+j*omega*t)")


@dataclass(frozen=True, slots=True)
class ImpedanceSpectrum:
    frequency_hz: np.ndarray
    impedance_ohm: np.ndarray
    valid: np.ndarray
    row_ids: tuple[str, ...]
    experiment_id: str
    source_id: str
    origin: Origin
    context: tuple[tuple[str, str], ...] = ()
    frequency_origin: Origin | None = field(default=None, kw_only=True)

    def __post_init__(self):
        frequencies = np.array(self.frequency_hz, dtype=float, copy=True)
        values = np.array(self.impedance_ohm, dtype=complex, copy=True)
        valid = np.array(self.valid, dtype=bool, copy=True)
        rows, context = tuple(self.row_ids), tuple(self.context)
        if frequencies.ndim != 1 or values.shape != frequencies.shape or valid.shape != frequencies.shape:
            raise ValueError("Spectrum frequency, complex response and masks need matching vectors")
        if len(rows) != len(values) or len(set(rows)) != len(rows) or any(not row for row in rows):
            raise ValueError("Each spectrum point needs its unique source-row identity")
        if not self.experiment_id or not self.source_id or len({key for key, _ in context}) != len(context):
            raise ValueError("Spectrum experiment/source and unique context keys are required")
        if np.any(valid & (~np.isfinite(frequencies) | (frequencies <= 0.) | ~np.isfinite(values))):
            raise ValueError("Valid spectrum points need positive finite frequency and finite impedance")
        for name, value in (("frequency_hz", frequencies), ("impedance_ohm", values), ("valid", valid)):
            value = immutable_array(value, name=name)
            object.__setattr__(self, name, value)
        object.__setattr__(self, "row_ids", rows)
        object.__setattr__(self, "context", context)
        object.__setattr__(self, "origin", Origin(self.origin))
        object.__setattr__(self, "frequency_origin", Origin(self.origin if self.frequency_origin is None
                                                          else self.frequency_origin))

    def cartesian_observations(self) -> ObservationTable:
        n = len(self.frequency_hz)
        values = np.column_stack((np.tile(self.frequency_hz, 2), np.repeat([0., 1.], n),
                                  np.concatenate((self.impedance_ohm.real, self.impedance_ohm.imag))))
        valid = np.tile(self.valid, 2)
        return ObservationTable(values, (FREQUENCY, COMPONENT, IMPEDANCE),
            np.column_stack((valid, np.ones(2*n, dtype=bool), valid)),
            tuple(row+suffix for suffix in ("/real", "/imag") for row in self.row_ids),
            (self.experiment_id,)*(2*n), (self.frequency_origin, Origin.RECONSTRUCTED, self.origin),
            self.source_id, self.context)
