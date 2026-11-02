"""Finite adsorption-vessel example with native CoolProp H2/N2 gas states.

The adsorption equilibrium remains an authored loading fixture; native fluid
properties do not establish material or device validation.
"""

import numpy as np

from h2physics.adapters.finite_adsorption_vessel import (
    AdsorptionVesselGeometry,
    FiniteAdsorptionVessel,
    FrozenGasBinding,
)
from h2physics.adsorption import AdsorptionBasis, AdsorptionState
from h2physics.mixtures import GasComposition
from h2physics.thermo import CoolPropMixtureProperties, CoolPropProperties


class AuthoredAbsoluteEquilibrium:
    """Example-only smooth loading fixture; replace with the native adapter."""

    basis = AdsorptionBasis(
        "authored-carbon", ("H2", "N2"), "mol/kg-dry-adsorbent",
        "authored-fixture", "authored-parameters", ("authored-example",), "absolute",
    )

    def equilibrium(self, partial_pressures_pa, temperature_k):
        partial = np.asarray(partial_pressures_pa, dtype=float)
        saturation = np.array([3.2, 1.0])[:, None]
        affinity = np.array([2.0e-7, 4.0e-7])[:, None]
        loading = saturation * affinity * partial[:, None] / (1 + affinity * partial[:, None])
        return AdsorptionState(self.basis, partial, temperature_k, loading)


def authored_vessel():
    composition = GasComposition(
        "authored-fixed-90-10-molar", ("H2", "N2"), (0.9, 0.1),
        (CoolPropProperties("Hydrogen").molar_mass_kg_mol,
         CoolPropProperties("Nitrogen").molar_mass_kg_mol),
    )
    properties = CoolPropMixtureProperties(
        composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
    )
    gas = FrozenGasBinding.bind(
        properties, species=composition.species,
        mole_fractions=composition.mole_fractions,
        molar_masses_kg_mol=composition.molar_masses_kg_mol,
        composition_id=composition.composition_id,
    )
    geometry = AdsorptionVesselGeometry(
        internal_volume_m3=0.12,
        adsorbent_mass_kg=42.,
        solid_envelope_volume_m3=0.035,
        inaccessible_volume_m3=0.005,
        volume_basis_id="authored-rigid-vessel-dimensions",
    )
    return FiniteAdsorptionVessel(
        vessel_id="authored-adsorption-vessel",
        geometry=geometry,
        adsorption=AuthoredAbsoluteEquilibrium(),
        gas=gas,
    )


def main():
    delivery = authored_vessel().delivery(
        10e6, 298.15, 1e6, 298.15, delivery_species=("H2",),
    )
    print(delivery.delivered_product_mol)


if __name__ == "__main__":
    main()
