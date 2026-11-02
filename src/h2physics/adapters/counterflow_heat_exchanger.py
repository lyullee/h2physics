"""Steady one-dimensional counterflow heat exchanger with caller-owned properties.

The model owns only cell heat transfer and the two stream enthalpy balances.
Absolute-pressure profiles and the ``state_ph`` property closure are supplied by
the caller, so no pressure-drop or equation-of-state model is duplicated here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import isclose

import numpy as np

from scipy.optimize import least_squares

from ..core import immutable_array, finite

STATUS = "implemented_unverified"


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    return value


def _readonly(values: Sequence[float], name: str, *, positive: bool = False) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    if result.ndim != 1 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite one-dimensional sequence")
    if positive and np.any(result <= 0.0):
        raise ValueError(f"{name} values must be positive")
    result = immutable_array(result, name="result")
    return result


@dataclass(frozen=True, slots=True)
class CounterflowDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_enthalpy_j_kg: float
    maximum_enthalpy_j_kg: float
    evidence_id: str

    def __post_init__(self):
        _text(self.evidence_id, "evidence_id")
        if (
            not 0.0
            < finite(self.minimum_temperature_k, "minimum_temperature_k")
            < finite(self.maximum_temperature_k, "maximum_temperature_k")
        ):
            raise ValueError("Temperature limits must be ordered and positive")
        if finite(self.minimum_enthalpy_j_kg, "minimum_enthalpy_j_kg") >= finite(
            self.maximum_enthalpy_j_kg, "maximum_enthalpy_j_kg"
        ):
            raise ValueError("Enthalpy limits must increase")


@dataclass(frozen=True, slots=True)
class CounterflowDefinition:
    equipment_id: str
    hot_stream_id: str
    cold_stream_id: str
    conductance_w_k: tuple[float, ...]
    conductance_source_id: str
    area_coordinate_source_id: str

    def __post_init__(self):
        for name in (
            "equipment_id",
            "hot_stream_id",
            "cold_stream_id",
            "conductance_source_id",
            "area_coordinate_source_id",
        ):
            _text(getattr(self, name), name)
        if self.hot_stream_id == self.cold_stream_id:
            raise ValueError("Hot and cold stream identities must differ")
        values = tuple(finite(x, "cell conductance", positive=True) for x in self.conductance_w_k)
        if not values:
            raise ValueError("At least one finite heat-transfer cell is required")
        object.__setattr__(self, "conductance_w_k", values)


@dataclass(frozen=True, slots=True)
class CounterflowBoundary:
    hot_mass_flow_kg_s: float
    cold_mass_flow_kg_s: float
    hot_inlet_enthalpy_j_kg: float
    cold_inlet_enthalpy_j_kg: float
    hot_pressure_pa_absolute: tuple[float, ...]
    cold_pressure_pa_absolute: tuple[float, ...]
    source_id: str

    def __post_init__(self):
        _text(self.source_id, "source_id")
        for name in ("hot_mass_flow_kg_s", "cold_mass_flow_kg_s"):
            finite(getattr(self, name), name, positive=True)
        for name in ("hot_inlet_enthalpy_j_kg", "cold_inlet_enthalpy_j_kg"):
            finite(getattr(self, name), name)
        for name in ("hot_pressure_pa_absolute", "cold_pressure_pa_absolute"):
            values = tuple(finite(x, name, positive=True) for x in getattr(self, name))
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class CounterflowResult:
    definition: CounterflowDefinition
    boundary: CounterflowBoundary
    hot_enthalpy_j_kg: np.ndarray
    cold_enthalpy_j_kg: np.ndarray
    hot_temperature_k: np.ndarray
    cold_temperature_k: np.ndarray
    cell_heat_w: np.ndarray
    hot_heat_loss_w: float
    cold_heat_gain_w: float
    global_energy_residual_w: float
    maximum_equation_residual: float
    solver_evaluations: int
    solver_message: str
    pressure_basis: str = "Pa_absolute"
    coordinate: str = "hot-inlet-to-hot-outlet; cold-flow-direction-is-reversed"

    def __post_init__(self):
        if not isinstance(self.definition, CounterflowDefinition) or not isinstance(
            self.boundary, CounterflowBoundary
        ):
            raise TypeError("Retain the typed exchanger definition and boundary")
        cells = len(self.definition.conductance_w_k)
        for name in (
            "hot_enthalpy_j_kg",
            "cold_enthalpy_j_kg",
            "hot_temperature_k",
            "cold_temperature_k",
            "cell_heat_w",
        ):
            object.__setattr__(self, name, _readonly(getattr(self, name), name))
            expected_size = cells if name == "cell_heat_w" else cells+1
            if getattr(self, name).size != expected_size:
                raise ValueError("Exchanger result arrays must match the original face/cell grid")
        for name in (
            "hot_heat_loss_w",
            "cold_heat_gain_w",
            "global_energy_residual_w",
            "maximum_equation_residual",
        ):
            finite(getattr(self, name), name)


class CounterflowHeatExchanger:
    """Solve cell-centred UA heat exchange using enthalpy as the primary state.

    ``state_ph(pressure_pa_absolute, enthalpy_j_kg)`` must return an object with
    finite ``temperature_k``. The caller retains ownership of phase selection,
    mixtures and property reference conventions.
    """

    def __init__(
        self,
        definition: CounterflowDefinition,
        *,
        hot_state_ph: Callable,
        cold_state_ph: Callable,
        domain: CounterflowDomain,
        equation_relative_tolerance: float = 1e-9,
        energy_absolute_tolerance_w: float = 1e-6,
        maximum_evaluations: int = 2000,
    ):
        if not isinstance(definition, CounterflowDefinition) or not isinstance(
            domain, CounterflowDomain
        ):
            raise TypeError("Supply typed exchanger definition and property domain")
        if not callable(hot_state_ph) or not callable(cold_state_ph):
            raise TypeError("Both streams require caller-owned state_ph closures")
        self.definition = definition
        self.hot_state_ph = hot_state_ph
        self.cold_state_ph = cold_state_ph
        self.domain = domain
        self.equation_relative_tolerance = finite(
            equation_relative_tolerance, "equation_relative_tolerance", positive=True
        )
        self.energy_absolute_tolerance_w = finite(
            energy_absolute_tolerance_w, "energy_absolute_tolerance_w", positive=True
        )
        if not isinstance(maximum_evaluations, int) or maximum_evaluations < 10:
            raise ValueError("maximum_evaluations must be an integer of at least ten")
        self.maximum_evaluations = maximum_evaluations

    def _temperature(self, factory, pressure, enthalpy):
        if not self.domain.minimum_enthalpy_j_kg <= enthalpy <= self.domain.maximum_enthalpy_j_kg:
            raise ValueError("Solver requested enthalpy outside the declared property domain")
        state = factory(float(pressure), float(enthalpy))
        # Rich thermodynamic providers must honor the requested PH pair. Minimal
        # temperature-only closures remain supported by the documented interface.
        for attribute, requested, absolute_tolerance in (
            ("pressure_pa", pressure, 1e-5),
            ("enthalpy_j_kg", enthalpy, 1e-5),
        ):
            supplied = getattr(state, attribute, None)
            if supplied is not None and not isclose(
                finite(supplied, attribute), requested,
                rel_tol=1e-9, abs_tol=absolute_tolerance,
            ):
                raise ValueError("Property closure returned a different pressure/enthalpy state")
        temperature = finite(getattr(state, "temperature_k"), "property temperature", positive=True)
        if (
            not self.domain.minimum_temperature_k
            <= temperature
            <= self.domain.maximum_temperature_k
        ):
            raise ValueError("Property result is outside the declared temperature domain")
        return temperature

    def solve(self, boundary: CounterflowBoundary) -> CounterflowResult:
        if not isinstance(boundary, CounterflowBoundary):
            raise TypeError("Supply a CounterflowBoundary")
        n = len(self.definition.conductance_w_k)
        if (
            len(boundary.hot_pressure_pa_absolute) != n + 1
            or len(boundary.cold_pressure_pa_absolute) != n + 1
        ):
            raise ValueError("Each caller pressure profile needs one value at every cell face")
        for enthalpy in (boundary.hot_inlet_enthalpy_j_kg, boundary.cold_inlet_enthalpy_j_kg):
            if (
                not self.domain.minimum_enthalpy_j_kg
                <= enthalpy
                <= self.domain.maximum_enthalpy_j_kg
            ):
                raise ValueError("Inlet enthalpy is outside the declared property domain")

        hot0 = boundary.hot_inlet_enthalpy_j_kg
        coldn = boundary.cold_inlet_enthalpy_j_kg
        hot_inlet_temperature = self._temperature(
            self.hot_state_ph, boundary.hot_pressure_pa_absolute[0], hot0
        )
        cold_inlet_temperature = self._temperature(
            self.cold_state_ph, boundary.cold_pressure_pa_absolute[-1], coldn
        )
        driving_temperature = max(abs(hot_inlet_temperature - cold_inlet_temperature), 1.0)
        scale = max(
            self.energy_absolute_tolerance_w,
            sum(self.definition.conductance_w_k) * driving_temperature,
            1e-12,
        )
        enthalpy_scale = scale / min(boundary.hot_mass_flow_kg_s, boundary.cold_mass_flow_kg_s)
        x0 = np.zeros(3 * n)
        lower = np.concatenate(
            (
                np.full(n, (self.domain.minimum_enthalpy_j_kg - hot0) / enthalpy_scale),
                np.full(n, (self.domain.minimum_enthalpy_j_kg - coldn) / enthalpy_scale),
                np.full(n, -np.inf),
            )
        )
        upper = np.concatenate(
            (
                np.full(n, (self.domain.maximum_enthalpy_j_kg - hot0) / enthalpy_scale),
                np.full(n, (self.domain.maximum_enthalpy_j_kg - coldn) / enthalpy_scale),
                np.full(n, np.inf),
            )
        )

        def unpack(x):
            hot_offset = np.concatenate(([0.0], enthalpy_scale * x[:n]))
            cold_offset = np.concatenate((enthalpy_scale * x[n : 2 * n], [0.0]))
            hot = hot0 + hot_offset
            cold = coldn + cold_offset
            return hot, cold, scale * x[2 * n :], hot_offset, cold_offset

        def equations(x):
            hot, cold, heat, hot_offset, cold_offset = unpack(x)
            residual = []
            for j, conductance in enumerate(self.definition.conductance_w_k):
                residual.append(
                    (boundary.hot_mass_flow_kg_s * (hot_offset[j] - hot_offset[j + 1]) - heat[j])
                    / scale
                )
                residual.append(
                    (boundary.cold_mass_flow_kg_s * (cold_offset[j] - cold_offset[j + 1]) - heat[j])
                    / scale
                )
                th = 0.5 * (
                    self._temperature(
                        self.hot_state_ph, boundary.hot_pressure_pa_absolute[j], hot[j]
                    )
                    + self._temperature(
                        self.hot_state_ph, boundary.hot_pressure_pa_absolute[j + 1], hot[j + 1]
                    )
                )
                tc = 0.5 * (
                    self._temperature(
                        self.cold_state_ph, boundary.cold_pressure_pa_absolute[j], cold[j]
                    )
                    + self._temperature(
                        self.cold_state_ph,
                        boundary.cold_pressure_pa_absolute[j + 1],
                        cold[j + 1],
                    )
                )
                residual.append((heat[j] - conductance * (th - tc)) / scale)
            return np.asarray(residual)

        solved = least_squares(
            equations,
            x0,
            bounds=(lower, upper),
            xtol=self.equation_relative_tolerance,
            ftol=self.equation_relative_tolerance,
            gtol=self.equation_relative_tolerance,
            max_nfev=self.maximum_evaluations,
        )
        residual = equations(solved.x)
        maximum_residual = float(np.max(np.abs(residual)))
        if not solved.success or maximum_residual > self.equation_relative_tolerance:
            raise RuntimeError(
                f"Counterflow equations did not close: {solved.message}; residual={maximum_residual}"
            )
        hot, cold, heat, _, _ = unpack(solved.x)
        hot_t = np.array(
            [
                self._temperature(self.hot_state_ph, p, h)
                for p, h in zip(boundary.hot_pressure_pa_absolute, hot, strict=True)
            ]
        )
        cold_t = np.array(
            [
                self._temperature(self.cold_state_ph, p, h)
                for p, h in zip(boundary.cold_pressure_pa_absolute, cold, strict=True)
            ]
        )
        hot_loss = boundary.hot_mass_flow_kg_s * (hot[0] - hot[-1])
        cold_gain = boundary.cold_mass_flow_kg_s * (cold[0] - cold[-1])
        global_residual = hot_loss - cold_gain
        limit = self.energy_absolute_tolerance_w + self.equation_relative_tolerance * max(
            abs(hot_loss), abs(cold_gain), 1.0
        )
        if abs(global_residual) > limit:
            raise RuntimeError(
                "Counterflow energy closure failed: "
                f"residual={global_residual:g} W exceeds {limit:g} W"
            )
        if np.any(heat <= 0.0):
            raise RuntimeError("Counterflow cell heat flow is nonpositive")
        if np.any(hot_t <= cold_t):
            raise RuntimeError("Counterflow hot-side temperature is not above the cold side")
        return CounterflowResult(
            self.definition,
            boundary,
            hot,
            cold,
            hot_t,
            cold_t,
            heat,
            hot_loss,
            cold_gain,
            global_residual,
            maximum_residual,
            int(solved.nfev),
            str(solved.message),
        )
