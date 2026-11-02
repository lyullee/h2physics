"""Native spin relaxation with explicit constant-pressure enthalpy accounting.

The native LH2DT module owns the rigid-rotor sum, rate, exact constant-T advance
and conversion heat. A thermostat and a finite constant-Cp calorimeter retain
spin enthalpy separately; neither supplies an evolving-spin fluid EOS or tank U.
Primary references: https://doi.org/10.1051/0004-6361/201527209 and
https://doi.org/10.1063/1.3160306.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from ..core import Origin, finite
from ..equipment import BoundaryPower


@dataclass(frozen=True, slots=True)
class SpinEvidence:
    rate_evidence_id: str
    conversion_enthalpy_evidence_id: str
    phase_scope_id: str
    source_ids: tuple[str, ...]
    parameter_origin: Origin

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() for value in (
                self.rate_evidence_id, self.conversion_enthalpy_evidence_id, self.phase_scope_id)):
            raise ValueError("Declare rate, conversion-enthalpy and phase-scope evidence")
        sources = tuple(self.source_ids)
        if not sources or any(not isinstance(value, str) or not value.strip() for value in sources):
            raise ValueError("Declare native/scientific or authored parameter-source identities")
        object.__setattr__(self, "source_ids", sources)
        object.__setattr__(self, "parameter_origin", Origin(self.parameter_origin))
        if self.parameter_origin == Origin.UNRESOLVED:
            raise ValueError("An unresolved rate/enthalpy origin cannot define a conversion model")


@dataclass(frozen=True, slots=True)
class SpinDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    reference_rotational_level: int
    cutoff_absolute_tolerance: float
    evidence_id: str

    def __post_init__(self):
        if finite(self.minimum_temperature_k, "minimum T", positive=True) >= finite(
                self.maximum_temperature_k, "maximum T", positive=True):
            raise ValueError("Spin temperature-domain bounds must increase")
        if (isinstance(self.reference_rotational_level, bool)
                or not isinstance(self.reference_rotational_level, int)
                or self.reference_rotational_level < 3):
            raise ValueError("Declare an integer reference rotational cutoff at least three")
        finite(self.cutoff_absolute_tolerance, "cutoff absolute tolerance", positive=True)
        if not self.evidence_id.strip():
            raise ValueError("Declare a temperature/cutoff-domain evidence identity")

    def require_temperature(self, temperature_k):
        temperature = finite(temperature_k, "temperature_k", positive=True)
        if not self.minimum_temperature_k <= temperature <= self.maximum_temperature_k:
            raise ValueError("Temperature is outside the declared native spin domain")
        return temperature


@dataclass(frozen=True, slots=True)
class SpinEnthalpyReference:
    """H_spin/M = h_ref + q*(x_ref-x); q is the native conversion enthalpy."""

    reference_para_fraction: float
    reference_specific_enthalpy_j_kg: float
    reference_id: str

    def __post_init__(self):
        if not 0 <= finite(self.reference_para_fraction, "reference para fraction") <= 1:
            raise ValueError("Reference para fraction must lie in [0, 1]")
        finite(self.reference_specific_enthalpy_j_kg, "reference spin enthalpy")
        if not self.reference_id.strip():
            raise ValueError("Spin enthalpy zero/reference identity is required")

    def enthalpy_j(self, mass_kg, para_fraction, conversion_enthalpy_j_kg):
        return mass_kg*(self.reference_specific_enthalpy_j_kg
                        + conversion_enthalpy_j_kg*(self.reference_para_fraction-para_fraction))


@dataclass(frozen=True, slots=True)
class SpinEquilibrium:
    temperature_k: float
    para_fraction: float
    reference_para_fraction: float
    cutoff_difference: float
    native_rotational_level: int
    reference_rotational_level: int


class SpinCutoffError(ValueError):
    def __init__(self, result):
        self.result = result
        super().__init__("Native rotational cutoff fails the declared larger-cutoff convergence gate")


@dataclass(frozen=True, slots=True)
class SpinRate:
    temperature_k: float
    mass_kg: float
    equilibrium: SpinEquilibrium
    para_fraction_rate_s: float
    conversion_heat_w: float
    native_state: Any
    native_parameters: Any


@dataclass(frozen=True, slots=True)
class SpinThermalSample:
    time_s: float
    temperature_k: float
    native_state: Any
    sensible_enthalpy_j: float
    spin_enthalpy_j: float
    conversion_heat_w: float
    external_power: BoundaryPower
    cumulative_external_heat_j: float
    enthalpy_balance_residual_j: float

    @property
    def total_enthalpy_j(self):
        return self.sensible_enthalpy_j+self.spin_enthalpy_j


@dataclass(frozen=True, slots=True)
class SpinThermalTrace:
    samples: tuple[SpinThermalSample, ...]
    clock_id: str
    pressure_pa: float
    mass_kg: float
    pressure_evidence_id: str
    enthalpy_reference: SpinEnthalpyReference
    kinetics: Any
    model_id: str
    sensible_heat_capacity_j_k: float | None = None
    sensible_evidence_id: str = ""
    native_solver_result: Any | None = None
    storage_constraint: str = "constant-pressure enthalpy; pressure/volume EOS unavailable"


def _times(time_s: Sequence[float], clock_id):
    values = np.asarray(time_s, dtype=float)
    if (values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values))
            or np.any(np.diff(values) <= 0)):
        raise ValueError("Spin times must be a finite increasing absolute clock")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("An absolute operation-clock identity is required")
    return values


def _pressure(pressure_pa, evidence_id):
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("Declare the held-pressure/calorimeter boundary evidence")
    return finite(pressure_pa, "held absolute pressure", positive=True)


class Lh2dtOrthoPara:
    """Actual native spin functions; rate and enthalpy remain caller evidence."""

    _parameter_names = ("conversion_rate_constant_s", "conversion_enthalpy_J_kg",
                        "rotational_temperature_K", "maximum_rotational_level")
    _functions = ("equilibrium_para_fraction", "para_fraction_rate_s",
                  "advance_ortho_para_state", "conversion_heat_rate_W")

    def __init__(self, native_module, native_parameters, *, evidence: SpinEvidence, domain: SpinDomain):
        if any(not callable(getattr(native_module, name, None)) for name in self._functions):
            raise TypeError("Supply the actual native ortho_para function module")
        if not isinstance(native_parameters, native_module.OrthoParaKineticsParameters):
            raise TypeError("Supply actual native OrthoParaKineticsParameters")
        self.native, self.parameters, self.evidence, self.domain = native_module, native_parameters, evidence, domain
        self._parameter_values = self._parameters()
        if domain.reference_rotational_level <= native_parameters.maximum_rotational_level:
            raise ValueError("Reference cutoff must exceed the selected native cutoff")

    def _parameters(self):
        rate, heat, theta = (finite(getattr(self.parameters, name), name)
                            for name in self._parameter_names[:3])
        cutoff = self.parameters.maximum_rotational_level
        if rate < 0 or heat < 0 or theta <= 0:
            raise ValueError("Native rate/gap must be nonnegative and rotational temperature positive")
        if isinstance(cutoff, bool) or not isinstance(cutoff, int) or cutoff < 1:
            raise ValueError("The native rotational cutoff must be an integer, not a boolean")
        return rate, heat, theta, cutoff

    def _identity(self):
        if self._parameters() != self._parameter_values:
            raise ValueError("Native spin parameters changed without rebinding their evidence")

    def state(self, para_fraction):
        if not 0 <= finite(para_fraction, "para fraction") <= 1:
            raise ValueError("Para fraction must lie in [0, 1]")
        return self.native.OrthoParaState(float(para_fraction))

    def _state(self, state):
        if not isinstance(state, self.native.OrthoParaState):
            raise TypeError("Retain an actual native OrthoParaState")
        if not 0 <= finite(state.para_fraction, "native para fraction") <= 1:
            raise ValueError("Native para fraction lies outside [0, 1]")

    def equilibrium(self, temperature_k):
        self._identity()
        temperature = self.domain.require_temperature(temperature_k)
        kwargs = {"rotational_temperature_K": self.parameters.rotational_temperature_K}
        value = self.native.equilibrium_para_fraction(temperature,
            maximum_rotational_level=self.parameters.maximum_rotational_level, **kwargs)
        reference = self.native.equilibrium_para_fraction(temperature,
            maximum_rotational_level=self.domain.reference_rotational_level, **kwargs)
        result = SpinEquilibrium(temperature, value, reference, abs(value-reference),
            self.parameters.maximum_rotational_level, self.domain.reference_rotational_level)
        if not 0 <= value <= 1 or result.cutoff_difference > self.domain.cutoff_absolute_tolerance:
            raise SpinCutoffError(result)
        return result

    def rate(self, state, temperature_k, mass_kg):
        self._state(state)
        mass = finite(mass_kg, "hydrogen mass", positive=True)
        equilibrium = self.equilibrium(temperature_k)
        rate = self.native.para_fraction_rate_s(state, equilibrium.temperature_k, self.parameters)
        heat = self.native.conversion_heat_rate_W(state, equilibrium.temperature_k, mass, self.parameters)
        return SpinRate(equilibrium.temperature_k, mass, equilibrium, rate, heat, state, self.parameters)

    def advance(self, state, temperature_k, time_step_s):
        self._state(state)
        temperature = self.equilibrium(temperature_k).temperature_k
        width = finite(time_step_s, "native exact-step duration")
        if width < 0:
            raise ValueError("Native spin step duration cannot be negative")
        result = self.native.advance_ortho_para_state(state, temperature, width, self.parameters)
        self._state(result)
        return result

    def thermostat(self, initial_state, *, temperature_k, mass_kg, pressure_pa,
                   time_s, clock_id, pressure_evidence_id, enthalpy_reference: SpinEnthalpyReference):
        times = _times(time_s, clock_id)
        pressure = _pressure(pressure_pa, pressure_evidence_id)
        first = self.rate(initial_state, temperature_k, mass_kg)
        gap = self.parameters.conversion_enthalpy_J_kg
        initial_h = enthalpy_reference.enthalpy_j(first.mass_kg, initial_state.para_fraction, gap)
        samples, state = [], initial_state
        for index, time in enumerate(times):
            if index:
                state = self.advance(state, temperature_k, float(time-times[index-1]))
            point = self.rate(state, temperature_k, mass_kg)
            enthalpy = enthalpy_reference.enthalpy_j(first.mass_kg, state.para_fraction, gap)
            # Exact integral follows the actual native composition change. Internal
            # conversion heat is not counted a second time as an external source.
            external_heat = -first.mass_kg*gap*(state.para_fraction-initial_state.para_fraction)
            residual = (enthalpy-initial_h)-external_heat
            samples.append(SpinThermalSample(float(time), point.temperature_k, state, 0., enthalpy,
                point.conversion_heat_w, BoundaryPower(heat_w=-point.conversion_heat_w),
                external_heat, residual))
        return SpinThermalTrace(tuple(samples), clock_id, pressure, first.mass_kg, pressure_evidence_id,
            enthalpy_reference, self, "native-exact-isothermal-spin-enthalpy-thermostat")


class Lh2dtSpinCalorimeter:
    """Finite constant-pressure, constant-Cp enthalpy coupling, without an EOS.

    Cp includes only caller-declared sensible storage at frozen composition.
    The native constant conversion gap is a separate spin enthalpy increment.
    Adiabatic conversion preserves total H, not rigid-vessel internal energy.
    """

    def __init__(self, kinetics: Lh2dtOrthoPara, *, mass_kg: float, pressure_pa: float,
                 pressure_evidence_id: str, sensible_heat_capacity_j_k: float,
                 sensible_evidence_id: str, enthalpy_reference: SpinEnthalpyReference,
                 reference_temperature_k: float, sensible_reference_enthalpy_j: float = 0.):
        self.kinetics, self.enthalpy_reference = kinetics, enthalpy_reference
        self.mass_kg = finite(mass_kg, "finite hydrogen mass", positive=True)
        self.pressure_pa = _pressure(pressure_pa, pressure_evidence_id)
        self.pressure_evidence_id = pressure_evidence_id
        self.sensible_heat_capacity_j_k = finite(sensible_heat_capacity_j_k, "sensible Cp", positive=True)
        if not isinstance(sensible_evidence_id, str) or not sensible_evidence_id.strip():
            raise ValueError("Declare sensible frozen-composition Cp and its enthalpy basis")
        self.sensible_evidence_id = sensible_evidence_id
        self.reference_temperature_k = finite(reference_temperature_k, "sensible reference T", positive=True)
        self.sensible_reference_enthalpy_j = finite(sensible_reference_enthalpy_j, "sensible enthalpy zero")

    def adiabatic(self, initial_state, *, temperature_k, time_s, clock_id, maximum_time_step_s,
                  relative_tolerance=1e-9, absolute_tolerance=1e-12):
        times = _times(time_s, clock_id)
        initial = self.kinetics.rate(initial_state, temperature_k, self.mass_kg)
        width = finite(maximum_time_step_s, "maximum coupled time step", positive=True)
        for tolerance in (relative_tolerance, absolute_tolerance):
            if not 0 < finite(tolerance, "coupled integration tolerance") < 1:
                raise ValueError("Coupled integration tolerances must lie in (0, 1)")
        gap = self.kinetics.parameters.conversion_enthalpy_J_kg
        capacity = self.sensible_heat_capacity_j_k
        fraction0 = initial_state.para_fraction

        def temperature(fraction):
            return initial.temperature_k+self.mass_kg*gap/capacity*(fraction-fraction0)

        def derivative(_time, values):
            state = self.kinetics.state(float(values[0]))
            return (self.kinetics.rate(state, temperature(state.para_fraction), self.mass_kg).para_fraction_rate_s,)

        solution = solve_ivp(derivative, (times[0], times[-1]), (fraction0,), t_eval=times,
            method="DOP853", rtol=relative_tolerance, atol=absolute_tolerance, max_step=width)
        if not solution.success:
            error = RuntimeError(f"Native-rate enthalpy coupling did not converge: {solution.message}")
            error.native_solver_result = solution
            raise error
        initial_spin = self.enthalpy_reference.enthalpy_j(self.mass_kg, fraction0, gap)
        sensible0 = (self.sensible_reference_enthalpy_j
                     + capacity*(initial.temperature_k-self.reference_temperature_k))
        samples = []
        for time, fraction in zip(solution.t, solution.y[0], strict=True):
            state = self.kinetics.state(float(fraction))
            temp = temperature(state.para_fraction)
            point = self.kinetics.rate(state, temp, self.mass_kg)
            sensible = sensible0+capacity*(temp-initial.temperature_k)
            spin = self.enthalpy_reference.enthalpy_j(self.mass_kg, state.para_fraction, gap)
            residual = ((sensible-sensible0)+(spin-initial_spin))
            samples.append(SpinThermalSample(float(time), temp, state, sensible, spin,
                point.conversion_heat_w, BoundaryPower(), 0., residual))
        return SpinThermalTrace(tuple(samples), clock_id, self.pressure_pa, self.mass_kg,
            self.pressure_evidence_id, self.enthalpy_reference, self.kinetics,
            "finite-constant-pressure-spin-enthalpy-calorimeter", capacity,
            self.sensible_evidence_id, solution)
