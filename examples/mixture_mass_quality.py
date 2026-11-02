"""Caller-configured native mass-quality query; no property work at import time."""

from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties


def saturation_from_mass_quality(
    properties: CoolPropMixtureProperties,
    *,
    pressure_pa: float,
    vapor_mass_fraction: float,
    native_mole_quality_bounds: tuple[float, float],
    branch_evidence_id: str,
    component_mole_balance_tolerance: float,
    mass_quality_absolute_tolerance: float,
    mole_quality_absolute_tolerance: float,
):
    """Return original native partition/root diagnostics on a supplied branch.

    The caller selects a supported composition and pressure. This function
    supplies no unqualified working mixture, phase envelope or default budget.
    It has not been executed in the coding-first development stage.
    """
    return properties.phase_partition_pq_mass(
        pressure_pa, vapor_mass_fraction,
        quality_bounds=native_mole_quality_bounds,
        branch_evidence_id=branch_evidence_id,
        component_mole_balance_tolerance=component_mole_balance_tolerance,
        mass_quality_absolute_tolerance=mass_quality_absolute_tolerance,
        quality_absolute_tolerance=mole_quality_absolute_tolerance,
    )
