"""Native deterministic transmitter response with explicit observation identity.

Native LH2DT owns filtering, scale/bias, clipping, quantization and stated bounds.
No sensor coefficients, random noise or historian clock alignment are inferred.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core import Origin, TimeSeries, finite
from ..observations import Variable


@dataclass(frozen=True, slots=True)
class TransmitterEvidence:
    instrument_id: str
    location_id: str
    variable: Variable
    calibration_id: str
    response_id: str
    source_ids: tuple[str, ...]
    parameter_origin: Origin

    def __post_init__(self):
        if any(not isinstance(x, str) or not x.strip() for x in (
                self.instrument_id, self.location_id, self.calibration_id, self.response_id)):
            raise ValueError("Instrument, location, calibration and response identities are required")
        if not isinstance(self.variable, Variable):
            raise TypeError("Declare the observed physical variable and its unit/basis")
        if self.variable.quantity in {"pressure", "pressure_difference"} and not self.variable.basis_id:
            raise ValueError("Instrument pressure needs an explicit absolute/gauge/differential basis")
        sources = tuple(self.source_ids)
        if not sources or any(not isinstance(x, str) or not x.strip() for x in sources):
            raise ValueError("Declare parameter-source or authored verification identities")
        object.__setattr__(self, "source_ids", sources)
        object.__setattr__(self, "parameter_origin", Origin(self.parameter_origin))


@dataclass(frozen=True, slots=True)
class TransmitterTrace:
    prediction: TimeSeries
    input_series: TimeSeries
    input_channel: str
    native_states: tuple[Any, ...]
    native_readings: tuple[Any, ...]
    native_transmitter: Any
    evidence: TransmitterEvidence
    hold_convention: str = "left-hold intervals; output is endpoint left limit"

    @property
    def final_native_state(self):
        return self.native_states[-1]


class TransmitterClosureError(RuntimeError):
    def __init__(self, message, *, native_state, native_reading):
        self.native_state, self.native_reading = native_state, native_reading
        super().__init__(message)


class Lh2dtTransmitter:
    """Evaluate the actual native instrument over a caller-declared held trajectory.

    At t[0], output reads the explicit initial native state. On (t[i],t[i+1])
    the driver is process[i]; output at t[i+1] is its left limit. In particular,
    the final process sample does not drive an additional unrecorded interval.
    An initial state is never guessed from an assumed sensor steady state.
    """

    _parameter_names = ("lower_range", "upper_range", "time_constant_s", "scale_factor",
                        "bias", "resolution", "accuracy_fraction_of_span")

    def __init__(self, native_transmitter, *, evidence: TransmitterEvidence):
        if not all(callable(getattr(native_transmitter, name, None))
                   for name in ("initialize", "advance", "read")):
            raise TypeError("Supply the actual native transmitter initialize/advance/read interface")
        if not isinstance(evidence, TransmitterEvidence):
            raise TypeError("Declare transmitter observation and parameter evidence")
        self.native, self.evidence = native_transmitter, evidence
        self.parameters = native_transmitter.parameters
        self._parameter_values = self._parameters()

    def _parameters(self):
        if self.native.parameters is not self.parameters:
            raise ValueError("Native transmitter parameter ownership changed; bind new evidence explicitly")
        values = tuple(finite(getattr(self.parameters, name), name) for name in self._parameter_names)
        low, high, tau, scale, _bias, resolution, accuracy = values
        if low >= high or tau < 0 or scale <= 0 or resolution < 0 or accuracy < 0:
            raise ValueError("Native transmitter parameters are outside the reviewed response domain")
        return values

    def _identity(self):
        if self._parameters() != self._parameter_values:
            raise ValueError("Native transmitter parameters changed without rebinding their evidence")

    def initialize(self, process_value: float):
        """Explicitly request native initial state; this does not infer a measured state."""
        self._identity()
        return self.native.initialize(finite(process_value, "initial process value"))

    def _reading(self, state, reading):
        try:
            filtered = finite(state.filtered_process_value, "native filtered state")
            names = ("indicated_value", "filtered_process_value", "unsaturated_indicated_value",
                     "quantization_error_bound", "stated_accuracy_bound")
            indicated, reported, raw, quantization, accuracy = (
                finite(getattr(reading, name), name) for name in names)
            if not isinstance(reading.saturated, (bool, np.bool_)):
                raise ValueError("Native saturation diagnostic must be boolean")
            if not self.parameters.lower_range <= indicated <= self.parameters.upper_range:
                raise ValueError("Native indication lies outside its declared range")
            tolerance = 1e-12*max(abs(filtered), abs(reported), 1.)
            if abs(filtered-reported) > tolerance or quantization < 0 or accuracy < 0:
                raise ValueError("Native reading state/bounds are inconsistent")
        except (ValueError, AttributeError, TypeError) as error:
            raise TransmitterClosureError(str(error), native_state=state,
                                          native_reading=reading) from error
        return indicated, filtered, raw, quantization, accuracy, float(reading.saturated)

    def run(self, process: TimeSeries, *, channel: str, initial_native_state,
            initial_time_s: float, location_id: str) -> TransmitterTrace:
        self._identity()
        if location_id != self.evidence.location_id:
            raise ValueError("Physical observation location differs from the declared instrument")
        if len(process.time_s) < 2 or finite(initial_time_s, "initial_time_s") != process.time_s[0]:
            raise ValueError("Initial native state time must equal the finite trajectory start")
        index = process.channels.index(channel)
        variable = Variable(channel, process.quantities[index], process.units[index],
                            process.basis_ids[index])
        self.evidence.variable.require_compatible(variable)
        if not np.all(process.valid[:, index]):
            raise ValueError("Missing process values need an explicit reconstruction; no hidden gap hold")
        states, readings, values = [initial_native_state], [], []
        reading = self.native.read(initial_native_state)
        readings.append(reading)
        values.append(self._reading(initial_native_state, reading))
        for left, right, value in zip(process.time_s[:-1], process.time_s[1:],
                                      process.values[:-1, index], strict=True):
            state, reading = self.native.advance(states[-1], float(value), float(right-left))
            states.append(state)
            readings.append(reading)
            values.append(self._reading(state, reading))
            self._identity()
        data = np.asarray(values)
        names = ("indicated", "filtered_process", "unsaturated_indication",
                 "quantization_bound", "stated_accuracy_bound", "saturated")
        unit, quantity, basis = variable.unit, variable.quantity, variable.basis_id
        prediction = TimeSeries(process.time_s, data, names, (unit,)*5+("1",),
            np.ones(data.shape, dtype=bool), process.clock_id, Origin.PREDICTED,
            f"{process.source_id}|native-transmitter:{self.evidence.instrument_id}",
            (quantity,)*3+(f"{quantity}_error_bound",)*2+("indication_flag",),
            (basis,)*5+("native deterministic range-saturation flag",))
        return TransmitterTrace(prediction, process, channel, tuple(states), tuple(readings),
                                self.native, self.evidence)
