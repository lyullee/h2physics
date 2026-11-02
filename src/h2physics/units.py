"""Small explicit unit conversions. Standard gas volume needs a reference state."""

import numpy as np

from .core import ThermoState, finite


def convert_to_si(values, *, quantity: str, unit: str, pressure_basis: str | None = None,
                  ambient_pressure_pa: float | None = None):
    values = np.asarray(values, dtype=float)
    factors = {
        "time": {"s": 1., "ms": .001, "min": 60., "h": 3600., "d": 86400.},
        "mass_flow": {"kg/s": 1., "g/s": .001, "kg/h": 1/3600.},
        "mass": {"kg": 1., "g": .001},
        "length": {"m": 1., "mm": .001, "cm": .01},
        "volume_fraction": {"1": 1., "%": .01, "ppm": 1e-6},
        "mole_fraction": {"1": 1., "%": .01, "ppm": 1e-6},
        "mass_fraction": {"1": 1., "%": .01, "wt%": .01},
        "voltage": {"V": 1., "mV": .001},
        "power": {"W": 1., "kW": 1000.},
        "current": {"A": 1., "mA": .001, "uA": 1e-6},
        "current_density": {"A/m2": 1., "A/cm2": 1e4, "mA/cm2": 10.},
        "energy": {"J": 1., "kJ": 1000.},
        "force": {"N": 1., "kN": 1000.},
        "relative_humidity": {"1": 1., "%": .01},
        "normalized_pressure": {"1": 1.},
        "specific_amount": {"mol/kg": 1., "mmol/g": 1., "mmol/kg": .001},
        "reference_specific_volume": {"m3/kg": 1., "cm3/g": .001},
    }
    if quantity == "temperature":
        if unit not in {"K", "degC"}:
            raise ValueError("Unsupported temperature unit")
        return values + (273.15 if unit == "degC" else 0.)
    if quantity in {"pressure", "pressure_difference", "reported_pressure"}:
        pressure_factors = {"Pa": 1., "kPa": 1e3, "MPa": 1e6, "bar": 1e5, "psi": 6894.757293168}
        if unit not in pressure_factors:
            raise ValueError("Unsupported pressure unit")
        result = values * pressure_factors[unit]
        if quantity == "reported_pressure":
            if pressure_basis is not None:
                raise ValueError("A reported pressure has unresolved semantics; declare a resolved pressure quantity instead")
            return result
        if quantity == "pressure_difference":
            if pressure_basis != "differential":
                raise ValueError("Differential pressure requires its separate declared basis")
            return result
        if pressure_basis == "absolute":
            return result
        if pressure_basis == "gauge" and ambient_pressure_pa is not None:
            return result + finite(ambient_pressure_pa, "ambient_pressure_pa", positive=True)
        raise ValueError("Pressure requires an absolute basis or gauge basis with ambient pressure")
    try:
        return values * factors[quantity][unit]
    except KeyError as error:
        raise ValueError(f"Unsupported conversion: {quantity}, {unit}") from error


def standard_volume_to_mass_flow(volume_flow_m3_s, reference_state: ThermoState):
    """The caller must supply the gas state used to define its standard volume."""
    if reference_state.phase not in {"gas", "supercritical_gas", "supercritical"}:
        raise ValueError("A standard-volume conversion requires an explicit gas reference state")
    return np.asarray(volume_flow_m3_s, dtype=float) * reference_state.density_kg_m3


def reference_specific_volume_to_amount(volume_m3_kg, reference_state: ThermoState,
                                       *, molar_mass_kg_mol: float):
    """Convert explicit reference gas volume to mol(entity)/kg of adsorbent.

    This only changes the gas-volume basis. It does not convert excess uptake
    to absolute uptake, infer a pore volume or choose an STP convention.
    """
    finite(molar_mass_kg_mol, "molar mass", positive=True)
    return standard_volume_to_mass_flow(volume_m3_kg, reference_state) / molar_mass_kg_mol
