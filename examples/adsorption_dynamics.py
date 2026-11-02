"""Synthetic API fixture for finite adsorption dynamics; not measured data."""

import numpy as np

from h2physics.adapters.finite_adsorption_vessel import (
    AdsorptionVesselGeometry,
    FiniteAdsorptionVessel,
    FrozenGasBinding,
)
from h2physics.adsorption import AdsorptionBasis, AdsorptionState
from h2physics.core import PropertyBasis, ThermoState


class SyntheticHydrogenGas:
    basis = PropertyBasis("synthetic-H2", "synthetic-h2-reference")
    molar_mass_kg_mol = 2.01588e-3
    gas_constant_j_mol_k = 8.31446261815324
    cv_j_mol_k = 20.4
    reference_temperature_k = 298.15

    def state_pt(self, pressure_pa, temperature_k):
        rho_mol = pressure_pa / (self.gas_constant_j_mol_k * temperature_k)
        density = rho_mol * self.molar_mass_kg_mol
        u_molar = self.cv_j_mol_k * (temperature_k - self.reference_temperature_k)
        u = u_molar / self.molar_mass_kg_mol
        h = (u_molar + self.gas_constant_j_mol_k * temperature_k) / self.molar_mass_kg_mol
        return ThermoState(self.basis, pressure_pa, temperature_k, density,
                           h, u, 0., "gas")

    def state_ph(self, pressure_pa, enthalpy_j_kg):
        raise NotImplementedError("The dynamic adsorption model only requests p,T states")

    def state_ps(self, pressure_pa, entropy_j_kg_k):
        raise NotImplementedError("The dynamic adsorption model only requests p,T states")


class SyntheticHydrogenAdsorption:
    basis = AdsorptionBasis("synthetic-carbon", ("H2",), "mol/kg-absolute",
                            "synthetic-Langmuir", "synthetic-v1",
                            ("authored-synthetic-fixture",), "absolute")

    def equilibrium(self, partial_pressures_pa, temperature_k):
        pressure = float(np.asarray(partial_pressures_pa)[0])
        affinity = np.array([1.0e-6, 3.0e-7])
        capacity = np.array([1.2, 0.7])
        loading = (capacity * affinity * pressure / (1. + affinity * pressure))[None, :]
        return AdsorptionState(self.basis, np.asarray([pressure]), temperature_k, loading)


def authored_dynamic_vessel():
    provider = SyntheticHydrogenGas()
    gas = FrozenGasBinding.bind(
        provider, species=("H2",), mole_fractions=(1.,),
        molar_masses_kg_mol=(provider.molar_mass_kg_mol,),
        composition_id="synthetic-pure-h2",
    )
    geometry = AdsorptionVesselGeometry(.08, 12., .015, .005, "synthetic-vessel-volume")
    return FiniteAdsorptionVessel(vessel_id="synthetic-dynamic-H2-vessel", geometry=geometry,
                                  adsorption=SyntheticHydrogenAdsorption(), gas=gas)
