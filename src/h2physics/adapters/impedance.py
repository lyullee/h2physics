"""Native impedance.py circuit objects as one complex observation operator.

The caller injects the actual installed circuit factory. No equivalent circuit
element, parser or frequency-domain solver is copied into this package.
"""

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core import immutable_array


from ..impedance import COMPONENT, FREQUENCY
from ..observations import ObservationTable


@dataclass(frozen=True, slots=True)
class NativeCircuitEvaluation:
    native: Any
    frequency_hz: np.ndarray
    impedance_ohm: np.ndarray
    parameter_names: tuple[str, ...]
    parameter_units: tuple[str, ...]

    def __post_init__(self):
        for name, dtype in (("frequency_hz", float), ("impedance_ohm", complex)):
            value = np.array(getattr(self, name), dtype=dtype, copy=True)
            value = immutable_array(value, name="value")
            object.__setattr__(self, name, value)


class NativeCircuitOperator:
    """Construct an actual native parameterized circuit for every evaluation.

    Prediction uses declared parameters. Native fit flags and covariance are
    not interpreted as experimental qualification or scientific uncertainty.
    """

    def __init__(self, factory: Callable[..., Any], *, circuit: str, parameter_names: tuple[str, ...],
                 parameter_units: tuple[str, ...] | None = None):
        if not circuit.strip() or not parameter_names or len(set(parameter_names)) != len(parameter_names):
            raise ValueError("Declare a native circuit and unique parameter names")
        self.factory, self.circuit, self.parameter_names = factory, circuit, tuple(parameter_names)
        if parameter_units is not None and len(parameter_units) != len(parameter_names):
            raise ValueError("Declared native units must identify every parameter")
        self.parameter_units = None if parameter_units is None else tuple(parameter_units)

    def evaluate(self, frequency_hz, parameters: Mapping[str, float]) -> NativeCircuitEvaluation:
        frequencies = np.asarray(frequency_hz, dtype=float)
        if frequencies.ndim != 1 or not len(frequencies) or np.any(~np.isfinite(frequencies) | (frequencies <= 0.)):
            raise ValueError("Native impedance prediction needs positive finite frequency samples")
        values = [float(parameters[name]) for name in self.parameter_names]
        if not np.all(np.isfinite(values)):
            raise ValueError("Native circuit parameters must be finite")
        native = self.factory(circuit=self.circuit, initial_guess=values)
        names, units = native.get_param_names()
        if tuple(names) != self.parameter_names or len(units) != len(names):
            raise ValueError("Native circuit parameter order differs from the declared contract")
        if self.parameter_units is not None and tuple(units) != self.parameter_units:
            raise ValueError("Native circuit parameter units differ from the declared contract")
        with warnings.catch_warnings():
            # This call deliberately predicts supplied parameters, without claiming a native fit.
            warnings.filterwarnings("ignore", message="Simulating circuit based on initial parameters",
                                    category=UserWarning, module=r"impedance\.models\.circuits\.circuits")
            predicted = np.asarray(native.predict(frequencies, use_initial=True), dtype=complex)
        if predicted.shape != frequencies.shape or not np.all(np.isfinite(predicted)):
            raise ValueError("Native circuit returned an invalid complex response")
        return NativeCircuitEvaluation(native, frequencies, predicted, tuple(names), tuple(units))

    def __call__(self, table: ObservationTable, parameters: Mapping[str, float]):
        frequencies, frequency_mask = table.column(FREQUENCY.name, expected=FREQUENCY)
        components, component_mask = table.column(COMPONENT.name, expected=COMPONENT)
        if not np.all(frequency_mask & component_mask) or np.any(~np.isin(components, (0., 1.))):
            raise ValueError("The Cartesian circuit operator needs valid real/imaginary selectors")
        response = self.evaluate(frequencies, parameters).impedance_ohm
        return np.where(components == 0., response.real, response.imag)
