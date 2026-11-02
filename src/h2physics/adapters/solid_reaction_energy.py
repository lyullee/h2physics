"""Provider-backed whole-system energy reconstruction for solid-reaction receipts."""

from math import fsum

import numpy as np

from ..core import finite
from ..thermochemical import FiniteThermochemicalCycle, ThermochemicalInventory


def inventory_enthalpy_j(inventory, *, species, provider, kernel, energy_basis_id):
    """Reconstruct one finite inventory enthalpy from its retained molar provider.

    The thermochemical kernel exposes per-species ``_h(T, P)`` for internal
    calculations but no total-inventory enthalpy method. This adapter helper
    deliberately uses the provider's public ``enthalpies_j_mol`` interface and
    the exact species ordering retained by the accepted reaction trace.
    """
    species = tuple(species)
    if type(inventory) is not ThermochemicalInventory:
        raise TypeError("Whole-system energy requires an admitted thermochemical inventory")
    if type(kernel) is not FiniteThermochemicalCycle:
        raise TypeError("Whole-system energy requires the retained finite-cycle kernel")
    names = tuple(item.identifier for item in species)
    if (not names or len(set(names)) != len(names)
            or tuple(provider.species) != species
            or kernel.enthalpy is not provider
            or tuple(kernel.species) != species
            or kernel.energy_basis_id != energy_basis_id
            or provider.basis_id != energy_basis_id
            or inventory.energy_basis_id != energy_basis_id
            or set(inventory.amounts_mol).difference(names)):
        raise ValueError("Inventory, kernel, provider species order and caloric reference must match the trace")
    temperature = finite(inventory.temperature_k, "inventory temperature", positive=True)
    pressure = finite(inventory.pressure_pa, "inventory absolute pressure", positive=True)
    molar_enthalpies = np.array(provider.enthalpies_j_mol(
        temperature, pressure), dtype=float, copy=True)
    if (molar_enthalpies.shape != (len(names),)
            or not np.all(np.isfinite(molar_enthalpies))):
        raise ValueError("Molar enthalpy provider returned invalid whole-system energy values")
    amounts = tuple(finite(inventory.amounts_mol.get(name, 0.), "inventory amount mol")
                    for name in names)
    if any(amount < 0. for amount in amounts):
        raise ValueError("Whole-system energy inventory amounts cannot be negative")
    return fsum(amount*float(enthalpy)
                for amount, enthalpy in zip(amounts, molar_enthalpies, strict=True))
