"""Transient one-dimensional radial conduction through a finite cylinder wall.

The model is axisymmetric, has no axial or circumferential gradients, and uses
caller-supplied temperature-dependent conductivity and heat capacity. Boundary
heat transfer is explicit on both wall faces. It is a thermal precursor that
can provide sampled profiles to the radial thermoelastic solver; it does not
solve mechanics, phase change, contact resistance, or a coupled fluid domain.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING

import numpy as np
from scipy.constants import Stefan_Boltzmann
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq
from scipy.sparse import lil_matrix

from ..core import finite, immutable_array

if TYPE_CHECKING:
    from .elastic_cylinder import (
        CylinderGeometry,
        CylinderPressureLoad,
        IsotropicThermoelasticMaterial,
    )
    from .radial_thermoelastic import RadialThermoelasticStressHistory


def _readonly(values):
    return immutable_array(values, dtype=float, name="radial heat array")


def _property(value, temperature_k, name, *, positive=False):
    result = finite(value(float(temperature_k)), name)
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class BoundedRadialProperty:
    """Guard one solid-property callback to an explicit absolute-K interval.

    Values are evaluated from the original caller function; this wrapper does
    not fit or interpolate properties. Every solver-time call is checked, so
    adaptive integration cannot silently query outside the declared domain.
    """

    function: Callable[[float], float]
    minimum_temperature_k: float
    maximum_temperature_k: float
    property_name: str
    evidence_id: str

    def __post_init__(self):
        if not callable(self.function):
            raise TypeError("A bounded radial property requires a callable")
        minimum = finite(self.minimum_temperature_k, "minimum property temperature", positive=True)
        maximum = finite(self.maximum_temperature_k, "maximum property temperature", positive=True)
        if maximum <= minimum:
            raise ValueError("Property temperature bounds must be strictly increasing")
        if (not isinstance(self.property_name, str) or not self.property_name.strip()
                or not isinstance(self.evidence_id, str) or not self.evidence_id.strip()):
            raise ValueError("Bounded properties require a name and evidence identity")
        object.__setattr__(self, "minimum_temperature_k", minimum)
        object.__setattr__(self, "maximum_temperature_k", maximum)

    def __call__(self, temperature_k: float) -> float:
        temperature = finite(temperature_k, "property evaluation temperature", positive=True)
        if not self.minimum_temperature_k <= temperature <= self.maximum_temperature_k:
            raise ValueError(
                f"{self.property_name} requested at {temperature:g} K outside its "
                f"declared [{self.minimum_temperature_k:g}, {self.maximum_temperature_k:g}] K domain"
            )
        return finite(self.function(temperature), self.property_name, positive=True)


def guard_radial_material_temperature_domain(
    material: RadialSolidMaterial,
    temperature_bounds_k: tuple[float, float],
    *,
    preflight_samples: int = 9,
) -> RadialSolidMaterial:
    """Return a material whose callbacks are preflighted and runtime-bounded.

    The finite preflight samples are admissibility checks only; they do not prove
    positivity between points, identify source uncertainty or validate a material
    over the interval. The solver rechecks the original functions at every call.
    """
    if type(material) is not RadialSolidMaterial:
        raise TypeError("Pass an actual RadialSolidMaterial")
    if len(temperature_bounds_k) != 2:
        raise ValueError("Declare exactly two material temperature bounds")
    lower = finite(temperature_bounds_k[0], "minimum material temperature", positive=True)
    upper = finite(temperature_bounds_k[1], "maximum material temperature", positive=True)
    if upper <= lower:
        raise ValueError("Material temperature bounds must be strictly increasing")
    if (isinstance(preflight_samples, bool) or not isinstance(preflight_samples, int)
            or preflight_samples < 2):
        raise ValueError("Preflight sample count must be an integer of at least two")
    heat_capacity = BoundedRadialProperty(
        material.heat_capacity_j_kg_k, lower, upper, "solid heat capacity", material.evidence_id
    )
    conductivity = BoundedRadialProperty(
        material.conductivity_w_m_k, lower, upper, "solid conductivity", material.evidence_id
    )
    samples = np.linspace(lower, upper, preflight_samples)
    for temperature in samples:
        heat_capacity(float(temperature))
        conductivity(float(temperature))
    return RadialSolidMaterial(
        material.density_kg_m3,
        heat_capacity,
        conductivity,
        material.material_id,
        material.evidence_id,
    )


def _history_array_signature(values):
    array = np.ascontiguousarray(values)
    return (array.dtype.str, array.shape, hashlib.sha256(array.tobytes()).hexdigest())


def _thermomechanical_signature(result):
    heat, stress = result.heat, result.stress
    heat_arrays = tuple(
        (name, _history_array_signature(getattr(heat, name)))
        for name in (
            "time_s", "radius_m", "temperature_k", "inner_heat_into_solid_j",
            "outer_heat_into_solid_j", "stored_energy_j", "energy_residual_j",
            "inner_surface_temperature_k", "outer_surface_temperature_k",
        )
    )
    stress_arrays = tuple(
        (name, _history_array_signature(getattr(stress, name)))
        for name in (
            "time_s", "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa", "axial_strain",
            "axial_support_reaction_n", "max_bvp_rms_residual",
            "max_normalized_boundary_residual",
        )
    )
    payload = (
        result.history_id, result.clock_id, result.evidence_id,
        heat_arrays, stress_arrays,
        (heat.inner_radius_m, heat.outer_radius_m, heat.cylinder_length_m,
         heat.reference_temperature_k, heat.history_id, heat.clock_id, heat.evidence_id,
         heat.material.density_kg_m3, heat.material.material_id, heat.material.evidence_id,
         id(heat.material.heat_capacity_j_kg_k), id(heat.material.conductivity_w_m_k),
         tuple((boundary.kind, str(boundary.value), boundary.evidence_id,
                str(boundary.coefficient))
               for boundary in (heat.inner_boundary, heat.outer_boundary))),
        (stress.geometry.inner_radius_m, stress.geometry.outer_radius_m,
         stress.geometry.end_condition, stress.geometry.geometry_id,
         stress.material.young_modulus_pa, stress.material.poisson_ratio,
         stress.material.linear_expansion_per_k, stress.material.material_id,
         stress.material.property_evidence_id, stress.axial_restraint,
         stress.clock_id, stress.evidence_id,
         tuple((load.internal_pressure_pa, load.external_pressure_pa,
                load.load_id, str(load.origin)) for load in stress.loads),
         tuple((profile.profile_id, profile.evidence_id,
                profile.reference_temperature_k,
                _history_array_signature(profile.radius_m),
                _history_array_signature(profile.temperature_k))
               for profile in stress.temperature_profiles)),
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


_PENDING_RADIAL_HEAT_ISSUERS = set()


def _issue_radial_heat_result(*values):
    token = object()
    _PENDING_RADIAL_HEAT_ISSUERS.add(token)
    try:
        return RadialHeatResult(*values, _issuer_token=token)
    except Exception:
        _PENDING_RADIAL_HEAT_ISSUERS.discard(token)
        raise


def _radial_heat_signature(result):
    arrays = tuple(
        (name, _history_array_signature(getattr(result, name)))
        for name in (
            "time_s", "radius_m", "temperature_k", "inner_heat_into_solid_j",
            "outer_heat_into_solid_j", "stored_energy_j", "energy_residual_j",
            "inner_surface_temperature_k", "outer_surface_temperature_k",
        )
    )
    payload = (
        arrays, result.inner_radius_m, result.outer_radius_m, result.cylinder_length_m,
        id(result.material), id(result.inner_boundary), id(result.outer_boundary),
        result.reference_temperature_k, id(result.native_solution), result.history_id,
        result.clock_id, result.evidence_id,
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class RadialSolidMaterial:
    """Homogeneous solid properties; callbacks return SI units at kelvin."""

    density_kg_m3: float
    heat_capacity_j_kg_k: Callable[[float], float]
    conductivity_w_m_k: Callable[[float], float]
    material_id: str
    evidence_id: str

    def __post_init__(self):
        density = finite(self.density_kg_m3, "solid density", positive=True)
        if not callable(self.heat_capacity_j_kg_k) or not callable(
            self.conductivity_w_m_k
        ):
            raise TypeError("Supply callable heat-capacity and conductivity properties")
        if (
            not isinstance(self.material_id, str)
            or not self.material_id.strip()
            or not isinstance(self.evidence_id, str)
            or not self.evidence_id.strip()
        ):
            raise ValueError("Solid properties need material and evidence identities")
        object.__setattr__(self, "density_kg_m3", density)


@dataclass(frozen=True, slots=True)
class RadialThermalBoundary:
    """One wall-face boundary; positive heat flux is directed into the solid.

    ``kind`` is ``adiabatic``, ``temperature``, ``heat_flux``, ``convection``
    or ``radiation``.
    A temperature boundary value is face temperature in K; heat flux is W/m2;
    convection value is fluid temperature in K and ``coefficient`` is W/m2/K.
    Scalar values or time-only callbacks may be supplied. For convection, the
    half-cell solid resistance and film resistance are placed in series. A
    radiation boundary uses an effective irradiation temperature in ``value``
    and an emissivity-view-factor product in ``coefficient``.
    """

    kind: str
    value: float | Callable[[float], float]
    evidence_id: str
    coefficient: float | Callable[[float], float] | None = None

    def __post_init__(self):
        if not isinstance(self.kind, str):
            raise ValueError("Thermal boundary kind must be a string identifier")
        if self.kind not in {
            "adiabatic",
            "temperature",
            "heat_flux",
            "convection",
            "radiation",
        }:
            raise ValueError("Unsupported radial thermal boundary kind")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Thermal boundary needs an evidence identity")
        if self.kind != "adiabatic" and not callable(self.value):
            finite(self.value, "thermal boundary value")
        if self.kind in {"convection", "radiation"}:
            if self.coefficient is None:
                raise ValueError("Convection/radiation needs an explicit exchange coefficient")
            if not callable(self.coefficient):
                coefficient = finite(self.coefficient, "boundary exchange coefficient")
                if self.kind == "convection" and coefficient <= 0:
                    raise ValueError("Convection coefficient must be positive")
                if self.kind == "radiation" and not 0 <= coefficient <= 1:
                    raise ValueError("Effective emissivity-view-factor must be in [0, 1]")
        elif self.coefficient is not None:
            raise ValueError("Only convection or radiation boundaries accept a coefficient")


@dataclass(frozen=True, slots=True)
class RadialHeatResult:
    """Cell-centered temperatures and an explicit global thermal ledger."""

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
    cylinder_length_m: float
    material: RadialSolidMaterial
    inner_boundary: RadialThermalBoundary
    outer_boundary: RadialThermalBoundary
    reference_temperature_k: float
    native_solution: object
    history_id: str
    clock_id: str
    evidence_id: str
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _content_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RADIAL_HEAT_ISSUERS:
            raise ValueError("Radial heat results are issued only by the native solver")
        _PENDING_RADIAL_HEAT_ISSUERS.remove(self._issuer_token)
        for name in (
            "time_s",
            "radius_m",
            "temperature_k",
            "inner_heat_into_solid_j",
            "outer_heat_into_solid_j",
            "stored_energy_j",
            "energy_residual_j",
            "inner_surface_temperature_k",
            "outer_surface_temperature_k",
        ):
            object.__setattr__(self, name, _readonly(getattr(self, name)))
        count = self.time_s.size
        if (
            self.time_s.ndim != 1
            or count < 2
            or not np.all(np.isfinite(self.time_s))
            or np.any(np.diff(self.time_s) <= 0)
        ):
            raise ValueError("Radial heat result times must be a nonempty increasing history")
        if (
            self.radius_m.ndim != 1
            or self.radius_m.size < 3
            or not np.all(np.isfinite(self.radius_m))
            or np.any(np.diff(self.radius_m) <= 0)
        ):
            raise ValueError("Radial cell-center radii must be finite and strictly increasing")
        inner = finite(self.inner_radius_m, "inner cylinder radius", positive=True)
        outer = finite(self.outer_radius_m, "outer cylinder radius", positive=True)
        finite(self.cylinder_length_m, "cylinder length", positive=True)
        if outer <= inner or self.radius_m[0] <= inner or self.radius_m[-1] >= outer:
            raise ValueError("Radial cell centers must lie inside the admitted wall")
        if type(self.material) is not RadialSolidMaterial:
            raise TypeError("Thermal result must retain its explicit solid material")
        if type(self.inner_boundary) is not RadialThermalBoundary or type(
            self.outer_boundary
        ) is not RadialThermalBoundary:
            raise TypeError("Thermal result must retain both face boundary models")
        finite(self.reference_temperature_k, "thermal enthalpy reference", positive=True)
        if not isinstance(self.history_id, str) or not self.history_id.strip():
            raise ValueError("Thermal history needs an explicit result identity")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Thermal history needs an explicit physical clock identity")
        if self.temperature_k.shape != (count, self.radius_m.size):
            raise ValueError("Temperature history must align with time and radial cells")
        if not np.all(np.isfinite(self.temperature_k)) or np.any(self.temperature_k <= 0):
            raise ValueError("Radial temperature result must be finite positive kelvin")
        for name in (
            "inner_heat_into_solid_j",
            "outer_heat_into_solid_j",
            "stored_energy_j",
            "energy_residual_j",
            "inner_surface_temperature_k",
            "outer_surface_temperature_k",
        ):
            values = getattr(self, name)
            if values.shape != (count,) or not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must be a finite vector aligned with time")
        expected_residual = (
            self.stored_energy_j
            - self.stored_energy_j[0]
            - self.inner_heat_into_solid_j
            - self.outer_heat_into_solid_j
        )
        energy_scale = max(
            float(np.max(np.abs(self.stored_energy_j - self.stored_energy_j[0]))),
            float(np.max(np.abs(self.inner_heat_into_solid_j))),
            float(np.max(np.abs(self.outer_heat_into_solid_j))),
            1.0,
        )
        if not np.allclose(
            self.energy_residual_j,
            expected_residual,
            rtol=2e-12,
            atol=2e-12 * energy_scale,
        ):
            raise ValueError("Energy residual must equal stored change minus both boundary heats")
        if self.inner_heat_into_solid_j[0] != 0.0 or self.outer_heat_into_solid_j[0] != 0.0:
            raise ValueError("Integrated boundary heat histories must start at zero")
        if np.any(self.inner_surface_temperature_k <= 0) or np.any(
            self.outer_surface_temperature_k <= 0
        ):
            raise ValueError("Surface temperatures must be positive absolute kelvin")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Model equation/applicability evidence identity is required")
        object.__setattr__(self, "_content_sha256", _radial_heat_signature(self))

    def require_current(self):
        if _radial_heat_signature(self) != self._content_sha256:
            raise ValueError("Radial heat result changed after native solver issuance")
        return self

    def thermoelastic_profile(
        self, index, *, reference_temperature_k, profile_evidence_id
    ):
        """Create a wall-surface-bounded temperature profile for the elastic solver."""
        self.require_current()
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < self.time_s.size
        ):
            raise IndexError("Select one valid temperature-history sample")
        if not isinstance(profile_evidence_id, str) or not profile_evidence_id.strip():
            raise ValueError("Identify evidence for the temperature-to-stress profile mapping")
        from .radial_thermoelastic import RadialTemperatureProfile

        return RadialTemperatureProfile(
            np.r_[self.inner_radius_m, self.radius_m, self.outer_radius_m],
            np.r_[
                self.inner_surface_temperature_k[index],
                self.temperature_k[index],
                self.outer_surface_temperature_k[index],
            ],
            reference_temperature_k,
            f"{self.history_id}:sample-{index}@{self.time_s[index]:.17g}s",
            f"{self.evidence_id};{profile_evidence_id}",
        )

    def thermoelastic_history(
        self,
        loads: tuple[CylinderPressureLoad, ...],
        geometry: CylinderGeometry,
        material: IsotropicThermoelasticMaterial,
        radius_m: float | np.ndarray,
        *,
        reference_temperature_k: float,
        axial_restraint: str,
        evidence_id: str,
        tolerance: float = 1.0e-7,
        max_nodes: int = 10_000,
    ) -> RadialThermomechanicalHistory:
        """Compose this wall-temperature history with matching pressure snapshots."""
        from .elastic_cylinder import CylinderGeometry, IsotropicThermoelasticMaterial
        from .radial_thermoelastic import (
            RadialThermoelasticHistoryError,
            radial_thermoelastic_history,
        )

        if type(geometry) is not CylinderGeometry:
            raise TypeError("Pass the actual cylinder geometry associated with this wall")
        if type(material) is not IsotropicThermoelasticMaterial:
            raise TypeError("Pass explicit isotropic thermoelastic material properties")
        if not np.isclose(geometry.inner_radius_m, self.inner_radius_m, rtol=0.0, atol=0.0):
            raise ValueError("Thermoelastic and thermal inner radii must match exactly")
        if not np.isclose(geometry.outer_radius_m, self.outer_radius_m, rtol=0.0, atol=0.0):
            raise ValueError("Thermoelastic and thermal outer radii must match exactly")
        profiles = tuple(
            self.thermoelastic_profile(
                index,
                reference_temperature_k=reference_temperature_k,
                profile_evidence_id=evidence_id,
            )
            for index in range(self.time_s.size)
        )
        try:
            stresses = radial_thermoelastic_history(
                geometry,
                tuple(loads),
                profiles,
                material,
                radius_m,
                self.time_s,
                axial_restraint=axial_restraint,
                clock_id=self.clock_id,
                evidence_id=evidence_id,
                tolerance=tolerance,
                max_nodes=max_nodes,
            )
        except RadialThermoelasticHistoryError as error:
            raise RadialThermomechanicalHistoryError(
                "Sequential thermal-to-thermoelastic composition failed",
                heat_history=self,
                failed_index=error.failed_index,
                completed_stress_fields=error.completed_fields,
                cause=error.cause,
            ) from error
        return RadialThermomechanicalHistory(
            self,
            stresses,
            self.history_id,
            self.clock_id,
            evidence_id,
        )


@dataclass(frozen=True, slots=True)
class RadialThermomechanicalHistory:
    """Paired thermal and quasi-static mechanical histories on one physical clock."""

    heat: RadialHeatResult
    stress: RadialThermoelasticStressHistory
    history_id: str
    clock_id: str
    evidence_id: str
    _identity_bindings: tuple = dataclass_field(default=(), init=False, repr=False, compare=False)
    _content_sha256: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        from .radial_thermoelastic import RadialThermoelasticStressHistory

        if type(self.heat) is not RadialHeatResult:
            raise TypeError("Thermomechanical history must retain its thermal result")
        self.heat.require_current()
        if type(self.stress) is not RadialThermoelasticStressHistory:
            raise TypeError("Thermomechanical history must retain its stress result")
        if type(self.history_id) is not str or not self.history_id.strip():
            raise ValueError("Thermomechanical history needs the originating heat identity")
        if type(self.clock_id) is not str or not self.clock_id.strip():
            raise ValueError("Thermomechanical history needs a physical clock identity")
        if type(self.evidence_id) is not str or not self.evidence_id.strip():
            raise ValueError("Thermomechanical history needs an equation/evidence identity")
        if not np.array_equal(self.heat.time_s, self.stress.time_s):
            raise ValueError("Thermal and mechanical histories must share sample times")
        if self.heat.clock_id != self.clock_id or self.stress.clock_id != self.clock_id:
            raise ValueError("Thermal and mechanical histories must share one clock identity")
        if self.heat.history_id != self.history_id:
            raise ValueError("Thermomechanical history must retain the originating heat ID")
        if self.stress.evidence_id != self.evidence_id:
            raise ValueError("Thermal-mechanical wrapper and stress history evidence must match")
        if len(self.stress.temperature_profiles) != self.heat.time_s.size:
            raise ValueError("Every heat sample must map to one thermoelastic profile")
        if self.stress.axial_restraint not in {"free", "fixed"}:
            raise ValueError("Thermoelastic history must retain an explicit axial restraint")
        if any(load is None for load in self.stress.loads):
            raise ValueError("Thermoelastic history must retain every pressure sample")
        if (
            self.stress.geometry.inner_radius_m != self.heat.inner_radius_m
            or self.stress.geometry.outer_radius_m != self.heat.outer_radius_m
        ):
            raise ValueError("Thermal and mechanical cylinder geometry must match")
        for index, profile in enumerate(self.stress.temperature_profiles):
            expected_profile_id = (
                f"{self.history_id}:sample-{index}@{self.heat.time_s[index]:.17g}s"
            )
            expected_radius = np.r_[
                self.heat.inner_radius_m,
                self.heat.radius_m,
                self.heat.outer_radius_m,
            ]
            expected_temperature = np.r_[
                self.heat.inner_surface_temperature_k[index],
                self.heat.temperature_k[index],
                self.heat.outer_surface_temperature_k[index],
            ]
            if profile.profile_id != expected_profile_id or not np.array_equal(
                profile.radius_m, expected_radius
            ) or not np.array_equal(profile.temperature_k, expected_temperature):
                raise ValueError("Stress inputs must retain the corresponding heat sample")
            expected_profile_evidence = f"{self.heat.evidence_id};{self.evidence_id}"
            if profile.evidence_id != expected_profile_evidence:
                raise ValueError("Thermoelastic profile must retain both thermal and stress evidence IDs")
        if not self.evidence_id.strip():
            raise ValueError("Thermomechanical composition needs an evidence identity")
        object.__setattr__(self, "_identity_bindings", (
            self.heat, self.stress, self.heat.material,
            self.heat.inner_boundary, self.heat.outer_boundary,
            self.stress.geometry, self.stress.material, self.stress.loads,
            self.stress.temperature_profiles,
            *self.stress.loads, *self.stress.temperature_profiles,
        ))
        object.__setattr__(self, "_content_sha256", _thermomechanical_signature(self))

    def require_current(self):
        current = (
            self.heat, self.stress, self.heat.material,
            self.heat.inner_boundary, self.heat.outer_boundary,
            self.stress.geometry, self.stress.material, self.stress.loads,
            self.stress.temperature_profiles,
            *self.stress.loads, *self.stress.temperature_profiles,
        )
        if not self._identity_bindings or any(
            value is not original
            for value, original in zip(current, self._identity_bindings, strict=True)
        ):
            raise ValueError("Thermomechanical history lost its original source/result objects")
        if _thermomechanical_signature(self) != self._content_sha256:
            raise ValueError("Thermal/mechanical history data or evidence changed after composition")
        return self


class RadialThermomechanicalHistoryError(RuntimeError):
    """Failed quasi-static sample with heat history and completed stress prefix retained."""

    def __init__(
        self,
        message,
        *,
        heat_history,
        failed_index,
        completed_stress_fields,
        cause,
    ):
        super().__init__(message)
        self.heat_history = heat_history
        self.failed_index = failed_index
        self.completed_stress_fields = tuple(completed_stress_fields)
        self.cause = cause


class RadialHeatIntegrationError(RuntimeError):
    """Rejected heat history with native progress or the triggering exception attached."""

    def __init__(self, message, *, native_solution=None, cause=None):
        super().__init__(message)
        self.native_solution = native_solution
        self.cause = cause


def radial_cylinder_heat_history(
    inner_radius_m: float,
    outer_radius_m: float,
    length_m: float,
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
) -> RadialHeatResult:
    """Integrate a finite cylindrical wall using conservative radial volumes.

    Internal heat rates use the exact cylindrical conduction resistance between
    radial nodes. Boundary ledgers are integrated as solver states, so the
    reported stored-energy residual compares the wall's temperature-dependent
    enthalpy change against both cumulative face heat inputs.
    """
    ri = finite(inner_radius_m, "inner cylinder radius", positive=True)
    ro = finite(outer_radius_m, "outer cylinder radius", positive=True)
    length = finite(length_m, "cylinder length", positive=True)
    if ro <= ri:
        raise ValueError("Cylinder outer radius must exceed its inner radius")
    if type(material) is not RadialSolidMaterial:
        raise TypeError("An explicit radial solid-material property record is required")
    if type(inner_boundary) is not RadialThermalBoundary or type(
        outer_boundary
    ) is not RadialThermalBoundary:
        raise TypeError("Both cylinder faces need explicit radial thermal boundaries")
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 3:
        raise ValueError("Use at least three radial finite volumes")
    if not evidence_id.strip():
        raise ValueError("Model equation/applicability evidence identity is required")
    if not history_id.strip():
        raise ValueError("Thermal history needs an explicit result identity")
    if not clock_id.strip():
        raise ValueError("Thermal history needs an explicit physical clock identity")
    times = np.asarray(time_s, dtype=float)
    if times.ndim != 1 or times.size < 2 or not np.all(np.isfinite(times)) or np.any(
        np.diff(times) <= 0
    ):
        raise ValueError("Output times must be finite and strictly increasing")
    faces = np.linspace(ri, ro, cells + 1)
    centers = np.sqrt((faces[:-1] ** 2 + faces[1:] ** 2) / 2.0)
    volumes = np.pi * length * np.diff(faces**2)
    inner_areas = 2.0 * np.pi * ri * length
    outer_areas = 2.0 * np.pi * ro * length
    initial_temperature = np.asarray(initial_temperature_k, dtype=float)
    if initial_temperature.ndim == 0:
        initial_temperature = np.full(cells, float(initial_temperature))
    if initial_temperature.shape != (cells,) or not np.all(np.isfinite(initial_temperature)) or np.any(
        initial_temperature <= 0
    ):
        raise ValueError("Initial temperature must be positive kelvin per radial cell")
    reference = (
        float(np.mean(initial_temperature))
        if reference_temperature_k is None
        else finite(reference_temperature_k, "enthalpy reference temperature", positive=True)
    )
    finite(relative_tolerance, "relative tolerance", positive=True)
    finite(absolute_tolerance_k, "absolute temperature tolerance", positive=True)
    if maximum_step_s <= 0 or np.isnan(maximum_step_s):
        raise ValueError("Maximum integration step must be positive")

    def boundary_heat(boundary, time, cell_temperature, center, face, area, conductivity):
        if boundary.kind == "adiabatic":
            return 0.0, cell_temperature
        supplied = boundary.value(time) if callable(boundary.value) else boundary.value
        supplied = finite(supplied, "radial boundary input")
        solid_resistance = abs(np.log(center / face)) / (
            2.0 * np.pi * length * conductivity
        )
        if boundary.kind == "heat_flux":
            return supplied * area, cell_temperature + supplied * area * solid_resistance
        if supplied <= 0:
            raise ValueError("Boundary temperatures must be positive absolute kelvin")
        if boundary.kind == "temperature":
            conductance = 1.0 / solid_resistance
            heat = conductance * (supplied - cell_temperature)
            surface_temperature = supplied
        elif boundary.kind == "radiation":
            emissivity_view = (
                boundary.coefficient(time)
                if callable(boundary.coefficient)
                else boundary.coefficient
            )
            emissivity_view = finite(emissivity_view, "effective emissivity-view-factor")
            if not 0 <= emissivity_view <= 1:
                raise ValueError("Effective emissivity-view-factor must be in [0, 1]")
            if emissivity_view == 0 or supplied == cell_temperature:
                return 0.0, cell_temperature

            def surface_balance(surface_temperature):
                radiative_into = (
                    emissivity_view
                    * Stefan_Boltzmann
                    * area
                    * (supplied**4 - surface_temperature**4)
                )
                conductive_into = (surface_temperature - cell_temperature) / solid_resistance
                return radiative_into - conductive_into

            surface_temperature = brentq(
                surface_balance,
                min(supplied, cell_temperature),
                max(supplied, cell_temperature),
            )
            heat = (surface_temperature - cell_temperature) / solid_resistance
        else:
            coefficient = boundary.coefficient(time) if callable(boundary.coefficient) else boundary.coefficient
            coefficient = finite(coefficient, "heat-transfer coefficient", positive=True)
            film_resistance = 1.0 / (coefficient * area)
            heat = (supplied - cell_temperature) / (solid_resistance + film_resistance)
            surface_temperature = supplied - heat * film_resistance
        if surface_temperature <= 0 or not np.isfinite(surface_temperature):
            raise ValueError("Boundary condition produced a nonphysical surface temperature")
        return heat, surface_temperature

    def rhs(time, state):
        temperature = state[:cells]
        conductivity = np.array(
            [
                _property(material.conductivity_w_m_k, value, "solid conductivity", positive=True)
                for value in temperature
            ]
        )
        capacity = np.array(
            [
                _property(material.heat_capacity_j_kg_k, value, "solid heat capacity", positive=True)
                for value in temperature
            ]
        )
        internal_rates = np.zeros(max(cells - 1, 0))
        inner_surface = outer_surface = np.nan
        inner_rate, inner_surface = boundary_heat(
            inner_boundary, time, temperature[0], centers[0], ri, inner_areas, conductivity[0]
        )
        outer_rate, outer_surface = boundary_heat(
            outer_boundary, time, temperature[-1], centers[-1], ro, outer_areas, conductivity[-1]
        )
        for face_index in range(1, cells):
            left, right = face_index - 1, face_index
            face_radius = faces[face_index]
            resistance = (
                np.log(face_radius / centers[left]) / conductivity[left]
                + np.log(centers[right] / face_radius) / conductivity[right]
            ) / (
                2.0 * np.pi * length
            )
            internal_rates[face_index - 1] = (
                temperature[left] - temperature[right]
            ) / resistance
        derivative = np.empty(cells + 2)
        cell_heat_rates = np.empty(cells)
        cell_heat_rates[0] = inner_rate - internal_rates[0]
        cell_heat_rates[-1] = internal_rates[-1] + outer_rate
        if cells > 2:
            cell_heat_rates[1:-1] = internal_rates[:-1] - internal_rates[1:]
        derivative[:cells] = cell_heat_rates / (
            material.density_kg_m3 * capacity * volumes
        )
        derivative[-2:] = (inner_rate, outer_rate)
        return derivative

    sparsity = lil_matrix((cells + 2, cells + 2), dtype=int)
    for index in range(cells):
        sparsity[index, max(index - 1, 0) : min(index + 2, cells)] = 1
    sparsity[cells, [0, cells]] = 1
    sparsity[cells + 1, [cells - 1, cells + 1]] = 1
    try:
        solution = solve_ivp(
            rhs,
            (times[0], times[-1]),
            np.r_[initial_temperature, 0.0, 0.0],
            method="BDF",
            t_eval=times,
            rtol=relative_tolerance,
            atol=np.r_[np.full(cells, absolute_tolerance_k), 1e-8, 1e-8],
            max_step=maximum_step_s,
            jac_sparsity=sparsity.tocsr(),
        )
    except Exception as error:
        raise RadialHeatIntegrationError(
            "Radial cylinder conduction failed inside the solver RHS",
            cause=error,
        ) from error
    if not solution.success or solution.y.shape[1] != times.size:
        raise RadialHeatIntegrationError(
            f"Radial cylinder conduction integration failed: {solution.message}",
            native_solution=solution,
        )
    temperatures = solution.y[:cells].T
    if not np.all(np.isfinite(temperatures)) or np.any(temperatures <= 0):
        raise RadialHeatIntegrationError(
            "Radial cylinder conduction left positive finite kelvin",
            native_solution=solution,
        )

    def total_energy(temperature):
        return sum(
            material.density_kg_m3
            * volumes[index]
            * quad(
                lambda value: _property(
                    material.heat_capacity_j_kg_k,
                    value,
                    "solid heat capacity",
                    positive=True,
                ),
                reference,
                float(temperature[index]),
                epsabs=1e-9,
                epsrel=1e-9,
            )[0]
            for index in range(cells)
        )

    try:
        stored = np.array([total_energy(row) for row in temperatures])
        inner_heat, outer_heat = solution.y[-2:]
        residual = stored - stored[0] - inner_heat - outer_heat
        inner_surface = np.empty(times.size)
        outer_surface = np.empty(times.size)
        for index, (time, row) in enumerate(zip(times, temperatures, strict=True)):
            kin = _property(
                material.conductivity_w_m_k, row[0], "solid conductivity", positive=True
            )
            kout = _property(
                material.conductivity_w_m_k,
                row[-1],
                "solid conductivity",
                positive=True,
            )
            _, inner_surface[index] = boundary_heat(
                inner_boundary, time, row[0], centers[0], ri, inner_areas, kin
            )
            _, outer_surface[index] = boundary_heat(
                outer_boundary, time, row[-1], centers[-1], ro, outer_areas, kout
            )
    except Exception as error:
        raise RadialHeatIntegrationError(
            "Radial cylinder conduction output/energy audit failed",
            native_solution=solution,
            cause=error,
        ) from error
    return _issue_radial_heat_result(
        times,
        centers,
        temperatures,
        inner_heat,
        outer_heat,
        stored,
        residual,
        inner_surface,
        outer_surface,
        ri,
        ro,
        length,
        material,
        inner_boundary,
        outer_boundary,
        reference,
        solution,
        history_id,
        clock_id,
        evidence_id,
    )


__all__ = [
    "BoundedRadialProperty",
    "RadialHeatIntegrationError",
    "RadialHeatResult",
    "RadialSolidMaterial",
    "RadialThermalBoundary",
    "RadialThermomechanicalHistory",
    "RadialThermomechanicalHistoryError",
    "guard_radial_material_temperature_domain",
    "radial_cylinder_heat_history",
]
