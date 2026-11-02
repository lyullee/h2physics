"""Measured-flow conditioning through the existing nozzle, without another flow law."""

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from .core import Origin, PropertyProvider, finite
from .release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult


@dataclass(frozen=True, slots=True)
class NozzlePressureInference:
    nozzle: NozzleResult
    observed_mass_flow_kg_s: float
    stagnation_temperature_k: float
    temperature_basis_id: str
    evidence_id: str
    sampled_pressure_pa: tuple[float, ...]
    sampled_mass_flow_kg_s: tuple[float, ...]
    forward_evaluations: int
    root_iterations: int
    origin: Origin = field(default=Origin.RECONSTRUCTED, init=False)

    @property
    def equivalent_stagnation_pressure_pa(self):
        return self.nozzle.upstream_stagnation.pressure_pa

    @property
    def relative_mass_error(self):
        return self.nozzle.mass_flow_kg_s/self.observed_mass_flow_kg_s-1.


def infer_nozzle_stagnation_pressure(
    properties: PropertyProvider, *, observed_mass_flow_kg_s: float,
    stagnation_temperature_k: float, temperature_basis_id: str, evidence_id: str,
    back_pressure_pa: float, opening: NozzleOpening,
    pressure_bounds_pa: tuple[float, float], relative_mass_tolerance: float = 1e-7,
    monotonic_samples: int = 17,
) -> NozzlePressureInference:
    """Invert one declared monotone gas path at fixed T0 and effective opening.

    An inferred pressure is an equivalent inlet under the stated temperature,
    area and isentropic assumptions. It is neither an independent flow prediction
    nor a measured pipe pressure. A sampled monotonicity check is numerical
    evidence within the supplied bracket, not a proof for another EOS/domain.
    """
    mass = finite(observed_mass_flow_kg_s, "observed forward mass flow", positive=True)
    temperature = finite(stagnation_temperature_k, "stagnation temperature", positive=True)
    back = finite(back_pressure_pa, "absolute back pressure", positive=True)
    tolerance = finite(relative_mass_tolerance, "relative mass tolerance", positive=True)
    if not evidence_id.strip() or not temperature_basis_id.strip():
        raise ValueError("Measured-flow evidence and the fixed temperature interpretation are required")
    if len(pressure_bounds_pa) != 2:
        raise ValueError("Declare two absolute pressure bounds")
    low, high = (finite(value, "pressure bound", positive=True) for value in pressure_bounds_pa)
    if low < back or high <= low or tolerance >= 1.:
        raise ValueError("The gas inversion needs increasing bounds at/above ambient and a strict mass gate")
    if isinstance(monotonic_samples, bool) or not isinstance(monotonic_samples, int) or monotonic_samples < 5:
        raise ValueError("At least five pressure samples are required for the gas-path check")
    finite(opening.effective_area_m2(1.), "open effective area", positive=True)
    kernel = HomogeneousIsentropicNozzle(properties)
    cache = {}

    def forward(pressure):
        pressure = float(pressure)
        if pressure not in cache:
            state = properties.state_pt(pressure, temperature)
            properties.basis.require_compatible(state.basis)
            if (state.phase not in {"gas", "supercritical_gas", "supercritical"}
                    or state.vapor_mass_fraction not in {None, 1.}):
                raise ValueError("Pressure inversion is limited to the declared single-gas inlet path")
            cache[pressure] = kernel.solve(state, back_pressure_pa=back, opening=opening)
        return cache[pressure]

    pressures = np.geomspace(low, high, monotonic_samples)
    pressures[0], pressures[-1] = low, high
    rates = np.array([forward(pressure).mass_flow_kg_s for pressure in pressures])
    if not np.all(np.isfinite(rates)) or np.any(np.diff(rates) <= 0.):
        raise ValueError("The sampled forward mass-flow path is not strictly increasing")
    if not rates[0] <= mass <= rates[-1]:
        raise ValueError(f"Observed flow {mass:g} kg/s lies outside the bracketed forward range "
                         f"[{rates[0]:g}, {rates[-1]:g}] kg/s")
    if mass in (rates[0], rates[-1]):
        pressure = low if mass == rates[0] else high
        iterations = 0
    else:
        log_pressure, result = brentq(
            lambda log_p: forward(math.exp(log_p)).mass_flow_kg_s/mass-1.,
            math.log(low), math.log(high), xtol=1e-12, rtol=1e-12, full_output=True,
        )
        if not result.converged:
            raise RuntimeError("The shared-nozzle pressure inversion did not converge")
        pressure, iterations = math.exp(log_pressure), result.iterations
    nozzle = forward(pressure)
    if abs(nozzle.mass_flow_kg_s/mass-1.) > tolerance:
        raise RuntimeError("The inferred pressure fails its independently checked mass-flow target")
    return NozzlePressureInference(nozzle, mass, temperature, temperature_basis_id, evidence_id,
        tuple(pressures), tuple(rates), len(cache), iterations)
