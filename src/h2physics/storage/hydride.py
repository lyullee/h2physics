"""Reservoir-driven, spatially uniform hydride kinetics and thermal capacitance.

Scientific context: https://doi.org/10.1016/j.ijhydene.2007.08.010 and
https://doi.org/10.1002/est2.504. Equations are implemented independently, with
no source-specific material coefficients. This reduced model does not solve
gas inventory, pressure gradients, a shell temperature or a complete vessel
energy balance. The caller owns the gas reservoir and any flow limitation.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np
from scipy.integrate import solve_ivp

from ..constants import R_J_MOL_K
from ..core import finite, immutable_array

Branch = Literal["absorption", "desorption"]

_PENDING_TRAJECTORY_ISSUERS: set[object] = set()


def _issue_trajectory_token():
    token = object()
    _PENDING_TRAJECTORY_ISSUERS.add(token)
    return token


class HydrideEquilibrium(Protocol):
    def fugacity_pa(self, temperature_k: float, fraction: float, branch: Branch) -> float: ...


@dataclass(frozen=True, slots=True)
class VanthoffPlateau:
    """Desorption-positive ΔH/ΔS per mole H2; optional log-fugacity slope/gap.

    ln(f_eq/f_ref) = ΔS/R − ΔH/(R T) + slope (x − 0.5) ± gap/2.
    This is a plateau approximation, not a full alpha/beta PCT equation.
    Use a different native equilibrium object for nonideal phase transitions.
    """

    desorption_enthalpy_j_mol_h2: float
    desorption_entropy_j_mol_h2_k: float
    reference_fugacity_pa: float
    log_fugacity_slope: float = 0.0
    log_hysteresis_gap: float = 0.0

    def __post_init__(self):
        finite(self.desorption_enthalpy_j_mol_h2, "desorption enthalpy", positive=True)
        finite(self.desorption_entropy_j_mol_h2_k, "desorption entropy")
        finite(self.reference_fugacity_pa, "reference fugacity", positive=True)
        finite(self.log_fugacity_slope, "plateau slope")
        if finite(self.log_hysteresis_gap, "log hysteresis gap") < 0:
            raise ValueError("The absorption/desorption fugacity gap cannot be negative")

    def fugacity_pa(self, temperature_k: float, fraction: float, branch: Branch) -> float:
        temperature_k = finite(temperature_k, "temperature", positive=True)
        fraction = _fraction(fraction)
        if branch not in {"absorption", "desorption"}:
            raise ValueError("Select an explicit hydride equilibrium branch")
        exponent = (self.desorption_entropy_j_mol_h2_k / R_J_MOL_K
                    - self.desorption_enthalpy_j_mol_h2 / (R_J_MOL_K * temperature_k)
                    + self.log_fugacity_slope * (fraction - 0.5)
                    + (0.5 if branch == "absorption" else -0.5) * self.log_hysteresis_gap)
        value = self.reference_fugacity_pa * math.exp(exponent)
        return finite(value, "equilibrium fugacity", positive=True)


@dataclass(frozen=True, slots=True)
class ArrheniusRate:
    rate_at_reference_s_inv: float
    activation_energy_j_mol: float
    reference_temperature_k: float

    def __post_init__(self):
        if finite(self.rate_at_reference_s_inv, "reference rate") < 0:
            raise ValueError("A kinetic rate cannot be negative")
        if finite(self.activation_energy_j_mol, "activation energy") < 0:
            raise ValueError("This rate law requires a nonnegative activation energy")
        finite(self.reference_temperature_k, "reference temperature", positive=True)

    def __call__(self, temperature_k: float) -> float:
        temperature_k = finite(temperature_k, "temperature", positive=True)
        return self.rate_at_reference_s_inv * math.exp(
            self.activation_energy_j_mol / R_J_MOL_K
            * (1 / self.reference_temperature_k - 1 / temperature_k))


@dataclass(frozen=True, slots=True)
class HydrideKinetics:
    equilibrium: HydrideEquilibrium
    absorption_rate: Callable[[float], float]
    desorption_rate: Callable[[float], float]

    def fraction_rate_s_inv(self, fraction: float, temperature_k: float,
                            hydrogen_fugacity_pa: float) -> float:
        fraction = _fraction(fraction)
        fugacity = finite(hydrogen_fugacity_pa, "hydrogen fugacity")
        if fugacity < 0:
            raise ValueError("Hydrogen fugacity cannot be negative")
        f_abs = self.equilibrium.fugacity_pa(temperature_k, fraction, "absorption")
        f_des = self.equilibrium.fugacity_pa(temperature_k, fraction, "desorption")
        if not (0 < f_des <= f_abs < math.inf):
            raise ValueError("Equilibrium branches overlap or have invalid fugacity")
        k_abs = finite(self.absorption_rate(temperature_k), "absorption rate")
        k_des = finite(self.desorption_rate(temperature_k), "desorption rate")
        if min(k_abs, k_des) < 0:
            raise ValueError("Kinetic callbacks must return nonnegative rates")
        return (k_abs * max(fugacity / f_abs - 1, 0) * (1 - fraction)
                - k_des * max(1 - fugacity / f_des, 0) * fraction)


@dataclass(frozen=True, slots=True)
class HydrideParameters:
    hydrogen_capacity_kg: float
    heat_capacity_j_k: float
    reaction_heat_j_mol_h2: float
    hydrogen_molar_mass_kg_mol: float
    ambient_conductance_w_k: float

    def __post_init__(self):
        for name in ("hydrogen_capacity_kg", "heat_capacity_j_k", "hydrogen_molar_mass_kg_mol"):
            finite(getattr(self, name), name, positive=True)
        for name in ("reaction_heat_j_mol_h2", "ambient_conductance_w_k"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} cannot be negative")

    @property
    def full_reaction_heat_j(self):
        return self.hydrogen_capacity_kg / self.hydrogen_molar_mass_kg_mol * self.reaction_heat_j_mol_h2

    def swing_capacity_kg(self, lower_fraction: float, upper_fraction: float) -> float:
        """Return nominal H2 mass between two declared bed-loading fractions.

        This is a capacity-window calculation only. It does not predict whether
        either endpoint is reachable at a given pressure, temperature, rate or
        cycle, and it does not account for inaccessible or degraded material.
        """
        lower = _fraction(lower_fraction)
        upper = _fraction(upper_fraction)
        if upper < lower:
            raise ValueError("upper loading fraction must be at least the lower fraction")
        return self.hydrogen_capacity_kg * (upper - lower)


@dataclass(frozen=True, slots=True)
class HydrideState:
    fraction: float
    temperature_k: float

    def __post_init__(self):
        _fraction(self.fraction)
        finite(self.temperature_k, "bed temperature", positive=True)


@dataclass(frozen=True, slots=True)
class HydrideBoundary:
    hydrogen_fugacity_pa: float
    bath_temperature_k: float
    external_heat_w: float = 0.0

    def __post_init__(self):
        if finite(self.hydrogen_fugacity_pa, "hydrogen fugacity") < 0:
            raise ValueError("Hydrogen fugacity cannot be negative")
        finite(self.bath_temperature_k, "bath temperature", positive=True)
        finite(self.external_heat_w, "external heat")


@dataclass(frozen=True, slots=True)
class HydrideRates:
    fraction_s_inv: float
    temperature_k_s: float
    hydrogen_uptake_kg_s: float
    reaction_heat_w: float
    boundary_heat_w: float


@dataclass(frozen=True, slots=True)
class HydrideTrajectory:
    time_s: np.ndarray
    fraction: np.ndarray
    temperature_k: np.ndarray
    hydrogen_stored_kg: np.ndarray
    integrated_boundary_heat_j: np.ndarray
    reduced_energy_residual_j: np.ndarray
    function_evaluations: int
    parameters: HydrideParameters
    initial_state: HydrideState
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRAJECTORY_ISSUERS:
            raise TypeError("Create hydride trajectories only from a completed integration")
        _PENDING_TRAJECTORY_ISSUERS.remove(self._issuer_token)
        if type(self.parameters) is not HydrideParameters or type(self.initial_state) is not HydrideState:
            raise TypeError("Hydride trajectory must retain its original material and initial state")
        names = ("time_s", "fraction", "temperature_k", "hydrogen_stored_kg",
                 "integrated_boundary_heat_j", "reduced_energy_residual_j")
        arrays = {}
        for name in names:
            values = np.asarray(getattr(self, name), dtype=float)
            if values.ndim != 1 or not np.all(np.isfinite(values)):
                raise ValueError(f"Hydride trajectory {name} must be a finite vector")
            arrays[name] = values
        time = arrays["time_s"]
        if len(time) < 2 or np.any(np.diff(time) <= 0.):
            raise ValueError("Hydride trajectory time must be strictly increasing")
        if any(arrays[name].shape != time.shape for name in names[1:]):
            raise ValueError("Hydride trajectory arrays must share one sample axis")
        fraction = arrays["fraction"]
        temperature = arrays["temperature_k"]
        stored = arrays["hydrogen_stored_kg"]
        heat = arrays["integrated_boundary_heat_j"]
        residual = arrays["reduced_energy_residual_j"]
        if np.any((fraction < 0.) | (fraction > 1.)) or np.any(temperature <= 0.):
            raise ValueError("Hydride trajectory states leave the physical fraction/temperature domain")
        if np.any(stored < 0.) or not np.array_equal(
                stored, self.parameters.hydrogen_capacity_kg*fraction):
            raise ValueError("Hydride trajectory stored mass differs from its retained capacity and loading")
        expected_residual = (
            self.parameters.heat_capacity_j_k*(temperature-self.initial_state.temperature_k)
            - self.parameters.full_reaction_heat_j*(fraction-self.initial_state.fraction)
            - heat
        )
        if not np.array_equal(residual, expected_residual):
            raise ValueError("Hydride trajectory reduced energy residual does not reconstruct")
        if heat[0] != 0. or residual[0] != 0.:
            raise ValueError("Hydride trajectory integrated heat and residual must start at zero")
        if type(self.function_evaluations) is not int or self.function_evaluations <= 0:
            raise ValueError("Hydride trajectory requires a positive native evaluation count")
        for name, values in arrays.items():
            object.__setattr__(self, name, immutable_array(values, name=name))


def _fraction(value):
    value = finite(value, "hydride fraction")
    if not 0 <= value <= 1:
        raise ValueError("Hydride fraction must lie in [0, 1]")
    return value


class HydrideBed:
    def __init__(self, parameters: HydrideParameters, kinetics: HydrideKinetics):
        self.parameters, self.kinetics = parameters, kinetics

    def rates(self, state: HydrideState, boundary: HydrideBoundary) -> HydrideRates:
        p = self.parameters
        rate = self.kinetics.fraction_rate_s_inv(state.fraction, state.temperature_k,
                                                boundary.hydrogen_fugacity_pa)
        reaction_heat = p.full_reaction_heat_j * rate
        boundary_heat = (p.ambient_conductance_w_k
                         * (boundary.bath_temperature_k - state.temperature_k)
                         + boundary.external_heat_w)
        return HydrideRates(rate, (reaction_heat + boundary_heat) / p.heat_capacity_j_k,
                            p.hydrogen_capacity_kg * rate, reaction_heat, boundary_heat)

    def simulate(self, time_s, initial: HydrideState,
                 boundary: Callable[[float, HydrideState], HydrideBoundary], *,
                 method: str = "Radau", relative_tolerance: float = 1e-8,
                 maximum_step_s: float = math.inf) -> HydrideTrajectory:
        """Integrate one continuous boundary interval; split runs at known discontinuities.

        Numerical trial fractions are bounded only when evaluating the rate law.
        Returned states are not clipped; an out-of-bounds solution raises an error.
        The third integrated state is an independent quadrature of boundary heat.
        """
        times = np.asarray(time_s, dtype=float)
        if times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise ValueError("Simulation times must be finite and strictly increasing")
        finite(relative_tolerance, "relative tolerance", positive=True)
        if maximum_step_s <= 0 or math.isnan(maximum_step_s):
            raise ValueError("The maximum solver step must be positive")

        def rhs(time, values):
            trial = HydrideState(float(np.clip(values[0], 0, 1)), values[1])
            rates = self.rates(trial, boundary(time, trial))
            return rates.fraction_s_inv, rates.temperature_k_s, rates.boundary_heat_w

        solution = solve_ivp(rhs, (times[0], times[-1]), [initial.fraction, initial.temperature_k, 0],
                             t_eval=times, method=method, rtol=relative_tolerance,
                             atol=[1e-11, 1e-7, 1e-6], max_step=maximum_step_s)
        if not solution.success:
            raise RuntimeError(f"Hydride integration failed: {solution.message}")
        fraction, temperature, heat = solution.y
        if np.any((fraction < 0) | (fraction > 1)) or np.any(temperature <= 0):
            raise RuntimeError("The hydride solution left its physical state domain")
        p = self.parameters
        residual = (p.heat_capacity_j_k * (temperature - initial.temperature_k)
                    - p.full_reaction_heat_j * (fraction - initial.fraction) - heat)
        return HydrideTrajectory(times, fraction, temperature, p.hydrogen_capacity_kg * fraction,
                                 heat, residual, solution.nfev, p, initial,
                                 _issue_trajectory_token())
