"""Elastic strain-energy ceilings for caller-authored vessel fragment cases.

The result is only a kinematic upper bound for one specified fragment mass.
It does not predict rupture, fragment mass, energy partition, or launch direction.
"""

from dataclasses import dataclass
import math

from .core import finite
from .materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad


@dataclass(frozen=True, slots=True)
class FragmentElasticEnergyBound:
    """Energy and speed ceiling for an explicitly selected fragment mass."""

    geometry_id: str
    pressure_load_id: str
    material_evidence_id: str
    fragment_id: str
    elastic_strain_energy_j: float
    fragment_energy_fraction: float
    available_fragment_energy_j: float
    fragment_mass_kg: float
    maximum_speed_m_s: float

    def __post_init__(self):
        for name in ("geometry_id", "pressure_load_id", "material_evidence_id", "fragment_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        for name in ("elastic_strain_energy_j", "available_fragment_energy_j"):
            finite(getattr(self, name), name)
            if getattr(self, name) < 0.:
                raise ValueError(f"{name} cannot be negative")
        fraction = finite(self.fragment_energy_fraction, "fragment_energy_fraction")
        if not 0. <= fraction <= 1.:
            raise ValueError("fragment_energy_fraction must lie in [0, 1]")
        mass = finite(self.fragment_mass_kg, "fragment_mass_kg", positive=True)
        speed = finite(self.maximum_speed_m_s, "maximum_speed_m_s")
        if speed < 0.:
            raise ValueError("maximum_speed_m_s cannot be negative")
        expected_energy = self.elastic_strain_energy_j * fraction
        expected_speed = math.sqrt(2. * expected_energy / mass)
        if (not math.isclose(self.available_fragment_energy_j, expected_energy,
                             rel_tol=2e-13, abs_tol=0.)
                or not math.isclose(speed, expected_speed, rel_tol=2e-13, abs_tol=0.)):
            raise ValueError("Fragment energy and speed must close against the declared elastic ceiling")


def bound_fragment_speed_from_elastic_energy(
    geometry: CylinderGeometry,
    pressure_load: CylinderPressureLoad,
    *,
    cylinder_length_m: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    fragment_mass_kg: float,
    fragment_energy_fraction: float,
    fragment_id: str,
    material_evidence_id: str,
) -> FragmentElasticEnergyBound:
    """Return a one-fragment speed ceiling from differential-pressure strain energy.

    The cylinder is long, uniform, isotropic, linear elastic and governed by
    the existing Lamé solution. The admitted load must be a differential
    pressure increment against a zero-pressure exterior. The end condition is
    taken from ``geometry``. End-cap, local crack, plastic, gas-expansion and
    fracture work are excluded. The caller supplies the fraction of stored
    elastic energy assigned to this one fragment; it is not inferred.
    """
    if type(geometry) is not CylinderGeometry or type(pressure_load) is not CylinderPressureLoad:
        raise TypeError("Retain the shared typed cylinder geometry and pressure load")
    length = finite(cylinder_length_m, "cylinder_length_m", positive=True)
    young = finite(youngs_modulus_pa, "youngs_modulus_pa", positive=True)
    poisson = finite(poisson_ratio, "poisson_ratio")
    if not -1. < poisson < .5:
        raise ValueError("Poisson ratio must lie inside the stable isotropic elastic range")
    if pressure_load.external_pressure_pa != 0.:
        raise ValueError("Pressure load must represent a differential-pressure increment with zero exterior")
    fragment_mass = finite(fragment_mass_kg, "fragment_mass_kg", positive=True)
    fraction = finite(fragment_energy_fraction, "fragment_energy_fraction")
    if not 0. <= fraction <= 1.:
        raise ValueError("fragment_energy_fraction must lie in [0, 1]")
    for name, value in (("fragment_id", fragment_id), ("material_evidence_id", material_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")

    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    pressure = pressure_load.internal_pressure_pa
    denominator = ro * ro - ri * ri
    a = pressure * ri * ri / denominator
    b = pressure * ri * ri * ro * ro / denominator
    axial = a if geometry.end_condition == "closed" else 0.
    uniform = 2. * (1. - poisson) * a * a + axial * axial - 4. * poisson * a * axial
    radial_integral = .5 * (ro * ro - ri * ri)
    inverse_radius_integral = .5 * (1. / (ri * ri) - 1. / (ro * ro))
    strain_energy = (math.pi * length / young) * (
        uniform * radial_integral + 2. * (1. + poisson) * b * b * inverse_radius_integral
    )
    strain_energy = finite(strain_energy, "elastic_strain_energy_j")
    if strain_energy < 0.:
        raise ArithmeticError("Linear-elastic strain-energy integral became negative")
    available = strain_energy * fraction
    speed = math.sqrt(2. * available / fragment_mass)
    return FragmentElasticEnergyBound(
        geometry.geometry_id, pressure_load.load_id, material_evidence_id, fragment_id,
        strain_energy, fraction, available, fragment_mass, speed,
    )
