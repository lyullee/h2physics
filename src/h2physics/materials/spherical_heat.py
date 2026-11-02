"""Transient radial heat conduction in a finite spherical shell.

This is a one-dimensional homogeneous-solid model with prescribed thermal
boundary histories. It shares the admitted radial material and boundary
contracts with the cylindrical wall model, while using spherical cell volumes,
surface areas and exact radial conduction resistances.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.constants import Stefan_Boltzmann
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq
from scipy.sparse import lil_matrix

from ..core import finite, immutable_array
from .radial_heat import RadialSolidMaterial, RadialThermalBoundary, _property


@dataclass(frozen=True, slots=True)
class SphericalShellHeatResult:
    """Immutable cell temperatures and boundary-energy ledger for a sphere."""

    time_s: np.ndarray
    radius_m: np.ndarray
    temperature_k: np.ndarray
    inner_heat_into_solid_j: np.ndarray
    outer_heat_into_solid_j: np.ndarray
    stored_energy_j: np.ndarray
    energy_residual_j: np.ndarray
    inner_surface_temperature_k: np.ndarray
    outer_surface_temperature_k: np.ndarray
    inner_radius_m: float
    outer_radius_m: float
    material: RadialSolidMaterial
    inner_boundary: RadialThermalBoundary
    outer_boundary: RadialThermalBoundary
    reference_temperature_k: float
    native_solution: object
    history_id: str
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        for name in (
            "time_s", "radius_m", "temperature_k", "inner_heat_into_solid_j",
            "outer_heat_into_solid_j", "stored_energy_j", "energy_residual_j",
            "inner_surface_temperature_k", "outer_surface_temperature_k",
        ):
            value = immutable_array(getattr(self, name), dtype=float, name=name)
            object.__setattr__(self, name, value)
        time = self.time_s
        radius = self.radius_m
        cells = radius.size
        if (time.ndim != 1 or time.size < 2 or not np.all(np.isfinite(time))
                or np.any(np.diff(time) <= 0)):
            raise ValueError("Spherical heat times must be finite and strictly increasing")
        if (radius.ndim != 1 or cells < 3 or not np.all(np.isfinite(radius))
                or np.any(np.diff(radius) <= 0)):
            raise ValueError("Spherical shell cell centers must be strictly increasing")
        inner = finite(self.inner_radius_m, "inner sphere radius", positive=True)
        outer = finite(self.outer_radius_m, "outer sphere radius", positive=True)
        if outer <= inner or radius[0] <= inner or radius[-1] >= outer:
            raise ValueError("Cell centers must remain strictly inside the spherical shell")
        if type(self.material) is not RadialSolidMaterial:
            raise TypeError("Spherical heat result must retain its radial material")
        if (type(self.inner_boundary) is not RadialThermalBoundary
                or type(self.outer_boundary) is not RadialThermalBoundary):
            raise TypeError("Spherical heat result must retain both boundary models")
        if self.temperature_k.shape != (time.size, cells):
            raise ValueError("Spherical temperature history must match time and cells")
        if not np.all(np.isfinite(self.temperature_k)) or np.any(self.temperature_k <= 0):
            raise ValueError("Spherical temperature values must be finite positive kelvin")
        for name in (
            "inner_heat_into_solid_j", "outer_heat_into_solid_j", "stored_energy_j",
            "energy_residual_j", "inner_surface_temperature_k", "outer_surface_temperature_k",
        ):
            values = getattr(self, name)
            if values.shape != time.shape or not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must be a finite series on the thermal clock")
        reference = finite(self.reference_temperature_k, "reference temperature", positive=True)
        expected = (self.stored_energy_j - self.stored_energy_j[0]
                    - self.inner_heat_into_solid_j - self.outer_heat_into_solid_j)
        scale = max(float(np.max(np.abs(expected))), 1.0)
        if not np.allclose(self.energy_residual_j, expected, rtol=2e-12, atol=2e-12*scale):
            raise ValueError("Spherical-wall energy residual disagrees with retained boundary heat")
        if self.inner_heat_into_solid_j[0] != 0 or self.outer_heat_into_solid_j[0] != 0:
            raise ValueError("Integrated boundary heat must start at zero")
        if (not isinstance(self.history_id, str) or not self.history_id.strip()
                or not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.evidence_id, str) or not self.evidence_id.strip()):
            raise ValueError("Spherical heat history requires result, clock and model evidence IDs")
        object.__setattr__(self, "inner_radius_m", inner)
        object.__setattr__(self, "outer_radius_m", outer)
        object.__setattr__(self, "reference_temperature_k", reference)


class SphericalShellHeatIntegrationError(RuntimeError):
    """Retain the native integration state when shell conduction fails."""

    def __init__(self, message, *, native_solution=None, cause=None):
        super().__init__(message)
        self.native_solution = native_solution
        self.cause = cause


def spherical_shell_heat_history(
    inner_radius_m: float,
    outer_radius_m: float,
    material: RadialSolidMaterial,
    initial_temperature_k,
    time_s,
    inner_boundary: RadialThermalBoundary,
    outer_boundary: RadialThermalBoundary,
    *,
    cells: int = 40,
    reference_temperature_k: float | None = None,
    relative_tolerance: float = 1e-7,
    absolute_tolerance_k: float = 1e-7,
    maximum_step_s: float = np.inf,
    history_id: str,
    clock_id: str,
    evidence_id: str,
) -> SphericalShellHeatResult:
    """Solve a finite spherical wall with caller-supplied radial thermal boundaries.

    Heat rates are positive into the shell. Material enthalpy and both boundary
    transfers are integrated independently, so the result exposes a sampled
    global energy residual. This model does not include a gas domain, stress,
    phase change, contact resistance or a sphere population.
    """
    inner = finite(inner_radius_m, "inner sphere radius", positive=True)
    outer = finite(outer_radius_m, "outer sphere radius", positive=True)
    if outer <= inner:
        raise ValueError("Spherical shell outer radius must exceed its inner radius")
    if type(material) is not RadialSolidMaterial:
        raise TypeError("Supply an explicit RadialSolidMaterial")
    if (type(inner_boundary) is not RadialThermalBoundary
            or type(outer_boundary) is not RadialThermalBoundary):
        raise TypeError("Both spherical shell faces need explicit RadialThermalBoundary objects")
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
        raise ValueError("Use at least three spherical radial finite volumes")
    if any(not isinstance(value, str) or not value.strip()
           for value in (history_id, clock_id, evidence_id)):
        raise ValueError("Declare result, physical clock and equation/applicability evidence IDs")
    times = np.asarray(time_s, dtype=float)
    if (times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times))
            or np.any(np.diff(times) <= 0)):
        raise ValueError("Output times must be finite and strictly increasing")
    faces = np.linspace(inner, outer, cells + 1)
    centers = 0.75 * (faces[1:]**4 - faces[:-1]**4) / (faces[1:]**3 - faces[:-1]**3)
    volumes = (4.0*np.pi/3.0) * np.diff(faces**3)
    inner_area, outer_area = 4.0*np.pi*inner**2, 4.0*np.pi*outer**2
    initial = np.asarray(initial_temperature_k, dtype=float)
    if initial.ndim == 0:
        initial = np.full(cells, float(initial))
    if initial.shape != (cells,) or not np.all(np.isfinite(initial)) or np.any(initial <= 0):
        raise ValueError("Initial temperature must be positive kelvin for every radial cell")
    reference = (float(np.mean(initial)) if reference_temperature_k is None
                 else finite(reference_temperature_k, "enthalpy reference temperature", positive=True))
    finite(relative_tolerance, "relative tolerance", positive=True)
    finite(absolute_tolerance_k, "absolute temperature tolerance", positive=True)
    maximum_step = float(maximum_step_s)
    if maximum_step <= 0 or np.isnan(maximum_step):
        raise ValueError("Maximum integration step must be positive")

    def solid_resistance(center, face, conductivity):
        return abs(1.0/center - 1.0/face) / (4.0*np.pi*conductivity)

    def boundary_heat(boundary, time, cell_t, center, face, area, conductivity):
        if boundary.kind == "adiabatic":
            return 0.0, cell_t
        supplied = boundary.value(time) if callable(boundary.value) else boundary.value
        supplied = finite(supplied, "spherical boundary input")
        resistance = solid_resistance(center, face, conductivity)
        if boundary.kind == "heat_flux":
            heat = supplied * area
            return heat, cell_t + heat*resistance
        if supplied <= 0:
            raise ValueError("Boundary temperatures must be positive absolute kelvin")
        if boundary.kind == "temperature":
            return (supplied-cell_t)/resistance, supplied
        if boundary.kind == "radiation":
            emissivity_view = boundary.coefficient(time) if callable(boundary.coefficient) else boundary.coefficient
            emissivity_view = finite(emissivity_view, "effective emissivity-view-factor")
            if not 0 <= emissivity_view <= 1:
                raise ValueError("Effective emissivity-view-factor must be in [0, 1]")
            if emissivity_view == 0 or supplied == cell_t:
                return 0.0, cell_t
            def surface_balance(surface_t):
                radiative = emissivity_view*Stefan_Boltzmann*area*(supplied**4-surface_t**4)
                conductive = (surface_t-cell_t)/resistance
                return radiative-conductive
            surface_t = brentq(surface_balance, min(supplied, cell_t), max(supplied, cell_t))
            return (surface_t-cell_t)/resistance, surface_t
        coefficient = boundary.coefficient(time) if callable(boundary.coefficient) else boundary.coefficient
        coefficient = finite(coefficient, "heat-transfer coefficient", positive=True)
        film_resistance = 1.0/(coefficient*area)
        heat = (supplied-cell_t)/(resistance+film_resistance)
        return heat, supplied-heat*film_resistance

    def rhs(time, state):
        temperature = state[:cells]
        conductivity = np.asarray([_property(material.conductivity_w_m_k, value,
            "solid conductivity", positive=True) for value in temperature])
        capacity = np.asarray([_property(material.heat_capacity_j_kg_k, value,
            "solid heat capacity", positive=True) for value in temperature])
        inner_rate, _ = boundary_heat(inner_boundary, time, temperature[0], centers[0],
                                      inner, inner_area, conductivity[0])
        outer_rate, _ = boundary_heat(outer_boundary, time, temperature[-1], centers[-1],
                                      outer, outer_area, conductivity[-1])
        internal = np.empty(cells-1)
        for i in range(cells-1):
            face = faces[i+1]
            resistance = ((1.0/conductivity[i])*(1.0/centers[i]-1.0/face)
                          +(1.0/conductivity[i+1])*(1.0/face-1.0/centers[i+1]))/(4.0*np.pi)
            internal[i] = (temperature[i]-temperature[i+1])/resistance
        heat = np.empty(cells)
        heat[0] = inner_rate-internal[0]
        heat[-1] = internal[-1]+outer_rate
        if cells > 2:
            heat[1:-1] = internal[:-1]-internal[1:]
        derivative = np.empty(cells+2)
        derivative[:cells] = heat/(material.density_kg_m3*capacity*volumes)
        derivative[-2:] = inner_rate, outer_rate
        return derivative

    sparsity = lil_matrix((cells+2, cells+2), dtype=int)
    for i in range(cells):
        sparsity[i, max(i-1, 0):min(i+2, cells)] = 1
    sparsity[cells, [0, cells]] = 1
    sparsity[cells+1, [cells-1, cells+1]] = 1
    try:
        solution = solve_ivp(rhs, (float(times[0]), float(times[-1])),
            np.r_[initial, 0.0, 0.0], method="BDF", t_eval=times,
            rtol=relative_tolerance,
            atol=np.r_[np.full(cells, absolute_tolerance_k), 1e-8, 1e-8],
            max_step=maximum_step, jac_sparsity=sparsity.tocsr())
    except Exception as error:
        raise SphericalShellHeatIntegrationError(
            "Spherical shell conduction failed inside the native solver RHS", cause=error) from error
    if not solution.success or solution.y.shape[1] != times.size:
        raise SphericalShellHeatIntegrationError(
            f"Spherical shell conduction integration failed: {solution.message}", native_solution=solution)
    temperatures = solution.y[:cells].T
    if not np.all(np.isfinite(temperatures)) or np.any(temperatures <= 0):
        raise SphericalShellHeatIntegrationError(
            "Spherical shell conduction left positive finite kelvin", native_solution=solution)

    def total_energy(row):
        total = 0.0
        for i, temperature in enumerate(row):
            cp_integral = quad(lambda value: _property(material.heat_capacity_j_kg_k,
                value, "solid heat capacity", positive=True), reference, float(temperature),
                epsabs=1e-9, epsrel=1e-9)[0]
            total += material.density_kg_m3*volumes[i]*cp_integral
        return total
    try:
        stored = np.asarray([total_energy(row) for row in temperatures])
    except Exception as error:
        raise SphericalShellHeatIntegrationError(
            "Spherical shell post-solve enthalpy audit failed",
            native_solution=solution, cause=error,
        ) from error
    inner_heat, outer_heat = solution.y[-2:]
    residual = stored-stored[0]-inner_heat-outer_heat
    surface_inner, surface_outer = np.empty(times.size), np.empty(times.size)
    try:
        for i, (time, row) in enumerate(zip(times, temperatures, strict=True)):
            _, surface_inner[i] = boundary_heat(inner_boundary, float(time), row[0], centers[0],
                inner, inner_area, _property(material.conductivity_w_m_k, row[0], "solid conductivity", positive=True))
            _, surface_outer[i] = boundary_heat(outer_boundary, float(time), row[-1], centers[-1],
                outer, outer_area, _property(material.conductivity_w_m_k, row[-1], "solid conductivity", positive=True))
        return SphericalShellHeatResult(
            times, centers, temperatures, inner_heat, outer_heat, stored, residual,
            surface_inner, surface_outer, inner, outer, material, inner_boundary,
            outer_boundary, reference, solution, history_id, clock_id, evidence_id,
        )
    except Exception as error:
        raise SphericalShellHeatIntegrationError(
            "Spherical shell post-solve result assembly failed",
            native_solution=solution, cause=error,
        ) from error


__all__ = ["SphericalShellHeatIntegrationError", "SphericalShellHeatResult",
           "spherical_shell_heat_history"]
