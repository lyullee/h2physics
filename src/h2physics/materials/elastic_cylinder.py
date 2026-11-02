"""Axisymmetric elastic stress reference for a thick cylinder under pressure.

This is a pressure-boundary stress model only. It does not infer a crack, residual
stress, plasticity, thermal load, end-cap detail, or fatigue geometry factor.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core import Origin, finite, immutable_array


@dataclass(frozen=True, slots=True)
class CylinderGeometry:
    """Uniform hollow-cylinder dimensions in SI units."""

    inner_radius_m: float
    outer_radius_m: float
    end_condition: str
    geometry_id: str

    def __post_init__(self):
        inner = finite(self.inner_radius_m, "cylinder inner radius", positive=True)
        outer = finite(self.outer_radius_m, "cylinder outer radius", positive=True)
        if outer <= inner:
            raise ValueError("Outer radius must exceed the positive inner radius")
        if self.end_condition not in {"closed", "open"}:
            raise ValueError("End condition must explicitly be closed or open")
        if not isinstance(self.geometry_id, str) or not self.geometry_id.strip():
            raise ValueError("A cylinder geometry identity is required")


@dataclass(frozen=True, slots=True)
class CylinderPressureLoad:
    """Uniform absolute pressures on the inner and outer cylinder surfaces."""

    internal_pressure_pa: float
    external_pressure_pa: float
    load_id: str
    origin: Origin

    def __post_init__(self):
        if finite(self.internal_pressure_pa, "internal absolute pressure") < 0:
            raise ValueError("Internal absolute pressure must be nonnegative")
        if finite(self.external_pressure_pa, "external absolute pressure") < 0:
            raise ValueError("External absolute pressure must be nonnegative")
        if not isinstance(self.load_id, str) or not self.load_id.strip():
            raise ValueError("A load identity is required")
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("An unresolved pressure load cannot be evaluated")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class CylinderStressField:
    """Returned Cauchy stress components; positive values denote tension."""

    radius_m: np.ndarray
    radial_stress_pa: np.ndarray
    hoop_stress_pa: np.ndarray
    axial_stress_pa: np.ndarray
    von_mises_stress_pa: np.ndarray
    geometry: CylinderGeometry
    load: CylinderPressureLoad
    evidence_id: str

    def __post_init__(self):
        if type(self.geometry) is not CylinderGeometry or type(self.load) is not CylinderPressureLoad:
            raise TypeError("Stress field must retain admitted cylinder geometry and pressure load")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Stress field requires an equation/applicability identity")
        arrays = []
        for name in (
            "radius_m", "radial_stress_pa", "hoop_stress_pa",
            "axial_stress_pa", "von_mises_stress_pa",
        ):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
                raise ValueError(f"Stress field {name} must be a nonempty finite vector")
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
            arrays.append(values)
        if any(values.shape != arrays[0].shape for values in arrays[1:]):
            raise ValueError("Stress field radius and component vectors must share one shape")
        if np.any((self.radius_m < self.geometry.inner_radius_m)
                  | (self.radius_m > self.geometry.outer_radius_m)):
            raise ValueError("Stress field radii must lie inside the cylinder wall")
        expected_vm = np.sqrt(0.5 * (
            (self.hoop_stress_pa - self.radial_stress_pa) ** 2
            + (self.radial_stress_pa - self.axial_stress_pa) ** 2
            + (self.axial_stress_pa - self.hoop_stress_pa) ** 2
        ))
        if not np.allclose(self.von_mises_stress_pa, expected_vm, rtol=2e-12, atol=1e-8):
            raise ValueError("Von Mises output does not match the principal stress components")


@dataclass(frozen=True, slots=True)
class CylinderStressSamples:
    """Pressure-driven stress fields evaluated only at supplied clock samples."""

    time_s: np.ndarray
    radius_m: np.ndarray
    radial_stress_pa: np.ndarray
    hoop_stress_pa: np.ndarray
    axial_stress_pa: np.ndarray
    von_mises_stress_pa: np.ndarray
    geometry: CylinderGeometry
    loads: tuple[CylinderPressureLoad, ...]
    evidence_id: str
    clock_id: str

    def __post_init__(self):
        if type(self.geometry) is not CylinderGeometry:
            raise TypeError("Sampled stress results must retain their cylinder geometry")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Sampled stress results require an evidence identity")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Sampled stress results require an explicit clock identity")
        loads = tuple(self.loads)
        if any(type(load) is not CylinderPressureLoad for load in loads):
            raise TypeError("Sampled stress results must retain admitted pressure loads")
        for name in (
            "time_s",
            "radius_m",
            "radial_stress_pa",
            "hoop_stress_pa",
            "axial_stress_pa",
            "von_mises_stress_pa",
        ):
            array = np.array(getattr(self, name), dtype=float, copy=True)
            if not np.all(np.isfinite(array)):
                raise ValueError(f"Sampled stress result {name} must be finite")
            array = immutable_array(array, name=name)
            object.__setattr__(self, name, array)
        if self.time_s.ndim != 1 or len(self.time_s) < 2:
            raise ValueError("Sampled stress results need at least two clock coordinates")
        if np.any(np.diff(self.time_s) <= 0) or len(loads) != len(self.time_s):
            raise ValueError("Sampled stress loads must match a strictly ordered clock")
        if self.radius_m.ndim != 1 or len(self.radius_m) == 0:
            raise ValueError("Sampled stress results need a nonempty one-dimensional radius grid")
        if (
            np.any(np.diff(self.radius_m) <= 0)
            or np.any(self.radius_m < self.geometry.inner_radius_m)
            or np.any(self.radius_m > self.geometry.outer_radius_m)
        ):
            raise ValueError("Sampled stress radii must increase inside the cylinder wall")
        shape = (len(self.time_s), len(self.radius_m))
        if any(
            getattr(self, name).shape != shape
            for name in (
                "radial_stress_pa",
                "hoop_stress_pa",
                "axial_stress_pa",
                "von_mises_stress_pa",
            )
        ):
            raise ValueError("Sampled stress component arrays must share the (time,radius) shape")
        object.__setattr__(self, "loads", loads)


@dataclass(frozen=True, slots=True)
class IsotropicThermoelasticMaterial:
    """Caller-supplied constant isotropic elastic and thermal properties."""

    young_modulus_pa: float
    poisson_ratio: float
    linear_expansion_per_k: float
    material_id: str
    property_evidence_id: str

    def __post_init__(self):
        young = finite(self.young_modulus_pa, "Young's modulus", positive=True)
        poisson = finite(self.poisson_ratio, "Poisson ratio")
        if not -1.0 < poisson < 0.5:
            raise ValueError("Isotropic elastic stability requires -1 < Poisson ratio < 0.5")
        expansion = finite(self.linear_expansion_per_k, "linear expansion coefficient")
        if not isinstance(self.material_id, str) or not self.material_id.strip():
            raise ValueError("A material identity is required")
        if not isinstance(self.property_evidence_id, str) or not self.property_evidence_id.strip():
            raise ValueError("Material-property evidence identity is required")
        object.__setattr__(self, "young_modulus_pa", young)
        object.__setattr__(self, "poisson_ratio", poisson)
        object.__setattr__(self, "linear_expansion_per_k", expansion)


@dataclass(frozen=True, slots=True)
class UniformCylinderTemperature:
    """Uniform wall temperature and explicit axial expansion boundary."""

    reference_temperature_k: float
    wall_temperature_k: float
    axial_restraint: str
    condition_id: str
    evidence_id: str

    def __post_init__(self):
        reference = finite(self.reference_temperature_k, "reference temperature", positive=True)
        temperature = finite(self.wall_temperature_k, "wall temperature", positive=True)
        if not isinstance(self.axial_restraint, str) or self.axial_restraint not in {
            "free",
            "fixed",
        }:
            raise ValueError("Axial restraint must be explicitly 'free' or 'fixed'")
        if not isinstance(self.condition_id, str) or not self.condition_id.strip():
            raise ValueError("A thermal/boundary-condition identity is required")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Temperature/support evidence identity is required")
        object.__setattr__(self, "reference_temperature_k", reference)
        object.__setattr__(self, "wall_temperature_k", temperature)


@dataclass(frozen=True, slots=True)
class ThermoelasticCylinderStressField:
    """Pressure plus uniform-temperature stress at caller-requested radii."""

    radius_m: np.ndarray
    radial_stress_pa: np.ndarray
    hoop_stress_pa: np.ndarray
    axial_stress_pa: np.ndarray
    von_mises_stress_pa: np.ndarray
    axial_support_reaction_n: float
    geometry: CylinderGeometry
    load: CylinderPressureLoad
    material: IsotropicThermoelasticMaterial
    temperature: UniformCylinderTemperature
    evidence_id: str

    def __post_init__(self):
        if (
            type(self.geometry) is not CylinderGeometry
            or type(self.load) is not CylinderPressureLoad
        ):
            raise TypeError("Thermoelastic result must retain its admitted geometry and load")
        if type(self.material) is not IsotropicThermoelasticMaterial:
            raise TypeError("Thermoelastic result must retain the material properties")
        if type(self.temperature) is not UniformCylinderTemperature:
            raise TypeError("Thermoelastic result must retain its thermal boundary condition")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Thermoelastic result requires an equation/applicability identity")
        arrays = []
        for name in (
            "radius_m",
            "radial_stress_pa",
            "hoop_stress_pa",
            "axial_stress_pa",
            "von_mises_stress_pa",
        ):
            array = np.array(getattr(self, name), dtype=float, copy=True)
            if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
                raise ValueError(f"Thermoelastic result {name} must be a finite vector")
            array = immutable_array(array, name=name)
            object.__setattr__(self, name, array)
            arrays.append(array)
        if any(array.shape != arrays[0].shape for array in arrays[1:]):
            raise ValueError("Thermoelastic stress and radius vectors must have the same shape")
        if np.any(np.diff(self.radius_m) <= 0):
            raise ValueError("Thermoelastic radii must be strictly increasing")
        if not np.all(
            (self.radius_m >= self.geometry.inner_radius_m)
            & (self.radius_m <= self.geometry.outer_radius_m)
        ):
            raise ValueError("Thermoelastic radii must lie inside the cylinder wall")
        reaction = finite(self.axial_support_reaction_n, "axial support reaction")
        object.__setattr__(self, "axial_support_reaction_n", reaction)


def lame_stress_field(
    geometry: CylinderGeometry,
    load: CylinderPressureLoad,
    radius_m: float | np.ndarray,
    *,
    evidence_id: str,
) -> CylinderStressField:
    """Evaluate the elastic Lamé field through a long, uniform cylinder wall.

    For radii ``ri <= r <= ro``, the radial and hoop stresses are
    ``A - B/r**2`` and ``A + B/r**2`` respectively, where
    ``A=(Pi*ri**2-Po*ro**2)/(ro**2-ri**2)`` and
    ``B=(Pi-Po)*ri**2*ro**2/(ro**2-ri**2)``. Closed ends use axial stress A;
    open ends use zero axial pressure stress. All inputs and outputs use metres
    and absolute Pa. The caller remains responsible for any reference/stress
    transformations, loads beyond uniform pressure, and applicability evidence.
    """
    if type(geometry) is not CylinderGeometry or type(load) is not CylinderPressureLoad:
        raise TypeError("Pass explicit cylinder geometry and pressure-load records")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("An equation/applicability evidence identity is required")
    radius = np.asarray(radius_m, dtype=float)
    if radius.ndim > 1 or radius.size == 0 or not np.all(np.isfinite(radius)):
        raise ValueError("Radius must be a finite scalar or one-dimensional array")
    if radius.ndim == 0:
        radius = radius.reshape(1)
    if np.any(radius < geometry.inner_radius_m) or np.any(radius > geometry.outer_radius_m):
        raise ValueError("Every radius must lie inside the cylinder wall")

    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    pi, po = load.internal_pressure_pa, load.external_pressure_pa
    denominator = ro * ro - ri * ri
    a_term = (pi * ri * ri - po * ro * ro) / denominator
    b_term = (pi - po) * ri * ri * ro * ro / denominator
    radial = a_term - b_term / (radius * radius)
    hoop = a_term + b_term / (radius * radius)
    axial = np.full_like(radius, a_term if geometry.end_condition == "closed" else 0.0)
    von_mises = np.sqrt(0.5 * ((hoop - radial) ** 2 + (radial - axial) ** 2 + (axial - hoop) ** 2))
    return CylinderStressField(radius, radial, hoop, axial, von_mises,
                                geometry, load, evidence_id)


def lame_stress_samples(
    geometry: CylinderGeometry,
    time_s: float | np.ndarray,
    loads: tuple[CylinderPressureLoad, ...] | list[CylinderPressureLoad],
    radius_m: float | np.ndarray,
    *,
    evidence_id: str,
    clock_id: str,
) -> CylinderStressSamples:
    """Evaluate Lamé fields for an ordered pressure series and requested radii.

    Output arrays have shape ``(number_of_times, number_of_radii)``. This is a
    sample transform only: no pressure interpolation, event localization, thermal
    stress, fatigue accumulation, or inter-sample extremum is inferred.
    """
    if type(geometry) is not CylinderGeometry:
        raise TypeError("Pass an explicit CylinderGeometry")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("An equation/applicability evidence identity is required")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("An explicit clock identity is required")
    loads = tuple(loads)
    times = np.asarray(time_s, dtype=float)
    if times.ndim == 0:
        times = times.reshape(1)
    if times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times)):
        raise ValueError("A stress series needs at least two finite clock samples")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Stress clock samples must be strictly increasing")
    if len(loads) != len(times) or any(type(load) is not CylinderPressureLoad for load in loads):
        raise ValueError("Provide one admitted pressure-load record per clock sample")

    fields = tuple(
        lame_stress_field(geometry, load, radius_m, evidence_id=evidence_id) for load in loads
    )
    radii = fields[0].radius_m
    arrays = [
        np.stack([getattr(field, name) for field in fields], axis=0)
        for name in (
            "radial_stress_pa",
            "hoop_stress_pa",
            "axial_stress_pa",
            "von_mises_stress_pa",
        )
    ]
    return CylinderStressSamples(
        times,
        radii,
        *arrays,
        geometry,
        loads,
        evidence_id,
        clock_id,
    )


def thermoelastic_lame_stress_field(
    geometry: CylinderGeometry,
    load: CylinderPressureLoad,
    radius_m: float | np.ndarray,
    material: IsotropicThermoelasticMaterial,
    temperature: UniformCylinderTemperature,
    *,
    evidence_id: str,
) -> ThermoelasticCylinderStressField:
    """Superpose Lamé pressure stress and uniform-temperature axial restraint.

    The material is homogeneous, isotropic, linearly elastic with constant
    properties. The wall temperature is spatially uniform. A free axial boundary
    retains the selected open/closed pressure result and develops no uniform-
    temperature stress. A fixed axial length imposes epsilon_z=0 and adds
    ``-E*alpha*delta_T + 2*nu*A`` to the axial field, where A is the constant
    Lamé stress sum from the pressure solution. Radial and hoop pressure stresses
    remain unchanged. The fixed-length result includes the net axial support
    reaction (wall axial resultant minus pressure end thrust on closed ends; positive
    along +z on the positive end). No through-wall thermal gradient, end region,
    plasticity or temperature-dependent property is represented.
    """
    if type(geometry) is not CylinderGeometry or type(load) is not CylinderPressureLoad:
        raise TypeError("Pass explicit cylinder geometry and pressure-load records")
    if type(material) is not IsotropicThermoelasticMaterial:
        raise TypeError("Pass explicit homogeneous isotropic thermoelastic properties")
    if type(temperature) is not UniformCylinderTemperature:
        raise TypeError("Pass an explicit uniform wall temperature and axial restraint")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("An equation/applicability evidence identity is required")

    pressure_field = lame_stress_field(geometry, load, radius_m, evidence_id=evidence_id)
    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    denominator = ro * ro - ri * ri
    a_term = (
        load.internal_pressure_pa * ri * ri - load.external_pressure_pa * ro * ro
    ) / denominator
    if temperature.axial_restraint == "fixed":
        axial_value = (
            2.0 * material.poisson_ratio * a_term
            - material.young_modulus_pa
            * material.linear_expansion_per_k
            * (temperature.wall_temperature_k - temperature.reference_temperature_k)
        )
        area = np.pi * denominator
        pressure_end_thrust = (
            np.pi
            * (load.internal_pressure_pa * ri * ri - load.external_pressure_pa * ro * ro)
            if geometry.end_condition == "closed"
            else 0.0
        )
        support_reaction = axial_value * area - pressure_end_thrust
    else:
        axial_value = float(pressure_field.axial_stress_pa[0])
        support_reaction = 0.0

    axial = np.full_like(pressure_field.radius_m, axial_value, dtype=float)
    radial = pressure_field.radial_stress_pa
    hoop = pressure_field.hoop_stress_pa
    von_mises = np.sqrt(
        0.5
        * (
            (hoop - radial) ** 2
            + (radial - axial) ** 2
            + (axial - hoop) ** 2
        )
    )
    return ThermoelasticCylinderStressField(
        pressure_field.radius_m,
        radial,
        hoop,
        axial,
        von_mises,
        support_reaction,
        geometry,
        load,
        material,
        temperature,
        evidence_id,
    )
