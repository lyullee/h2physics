"""Authored direct-DC settings with native CoolProp reaction calorimetry.

Electrical settings are illustrative inputs, not measured device parameters.
"""

import sys
from pathlib import Path

from h2physics.adapters.pv_electrolysis import (
    DirectDCDomain,
    NativePV,
    ProductPressureBoundary,
    PVBoundaryEvidence,
    PVBoundaryProfile,
    PVBoundarySample,
    PVElectrolysis,
    PVStage,
)
from h2physics.core import Origin
from h2physics.electrochemistry import HydrogenStack, OhmicLoss, ReactionEnergy, StackGeometry
from h2physics.reactions import ChemicalSpecies, StoichiometricReaction
from h2physics.storage.finite_hydride import HydrideGasThermodynamics
from h2physics.thermo import CoolPropMolarEnthalpy, CoolPropProperties

STATUS = "implemented_unverified"


def build_model(*, native_packages=None, maximum_current_density=1500.,
                source_pressure_pa=3e5, maximum_receiver_pressure_pa=2.5e5,
                faradaic_efficiency=1.):
    """Called only by the user/HPC case. Parameters are synthetic, not fitted."""
    if native_packages is not None:
        selected = str(Path(native_packages).resolve())
        if selected not in sys.path:
            sys.path.append(selected)
    native = NativePV.from_installed()
    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    # Original authored diode parameters: no module table is copied/retrieved.
    module = {"alpha_sc": .0038, "a_ref": 1.6, "I_L_ref": 8.2, "I_o_ref": 2e-7,
              "R_sh_ref": 240., "R_s": .18, "EgRef": 1.12, "dEgdT": -.00025,
              "irrad_ref": 1000., "temp_ref": 25.}
    system = native.pvsystem.PVSystem(module_parameters=module, modules_per_string=1,
                                      strings_per_inverter=1)
    oxygen_properties = CoolPropProperties("Oxygen")
    water_properties = CoolPropProperties("Water")
    mass_h2 = gas.molar_mass_kg_mol
    oxygen_atom_mass = 0.5 * oxygen_properties.molar_mass_kg_mol
    # Use one H/O atomic-weight basis for reaction mass bookkeeping; native
    # molar enthalpies retain each CoolProp fluid's own molar definition.
    water = ChemicalSpecies("water", {"H": 2, "O": 1}, mass_h2+oxygen_atom_mass, "liquid")
    hydrogen = ChemicalSpecies("hydrogen", {"H": 2}, mass_h2, "gas")
    oxygen = ChemicalSpecies("oxygen", {"O": 2}, 2*oxygen_atom_mass, "gas")
    reaction = StoichiometricReaction("authored-water-splitting", (water, hydrogen, oxygen),
                                      (-1., 1., .5))
    reference = "CoolProp-HEOS-native-H2-O2+NIST-liquid-water-formation-reference"
    reference_t, reference_p = 298.15, 101325.0
    hydrogen_reference = gas.state_pt(reference_p, reference_t).enthalpy_j_kg * mass_h2
    oxygen_reference = (oxygen_properties.state_pt(reference_p, reference_t).enthalpy_j_kg
                        * oxygen_properties.molar_mass_kg_mol)
    water_reference = (water_properties.state_pt(reference_p, reference_t).enthalpy_j_kg
                       * water_properties.molar_mass_kg_mol)
    # NIST water formation enthalpy at 298.15 K on the standard liquid basis:
    # https://webbook.nist.gov/cgi/cbook.cgi?Name=water&cTC=on&cTG=on
    # Leave H2/O2 on their native zeros and shift water by the same elemental
    # reference. This preserves the native H2 enthalpy gate at the product port.
    water_offset = -285830.0 + hydrogen_reference + 0.5 * oxygen_reference - water_reference
    caloric = CoolPropMolarEnthalpy(
        (water, hydrogen, oxygen), ("Water", "Hydrogen", "Oxygen"),
        (water_offset, 0.0, 0.0), basis_id=reference,
        temperature_bounds_k=(280., 360.), pressure_bounds_pa=(2e4, 5e5))

    def reaction_energy(t):
        h = caloric.enthalpies_j_mol(t, source_pressure_pa)
        # Gibbs energy remains an authored electrical input; CoolProp supplies
        # actual state enthalpies and does not establish device reversibility.
        return ReactionEnergy(220000., float(-h[0] + h[1] + 0.5 * h[2]), reference, "liquid")

    stack = HydrogenStack(StackGeometry(14, .01, mass_h2),
        reaction_energy,
        {"authored-ohmic": OhmicLoss(lambda t: .0004)})
    return PVElectrolysis(native, system, stack, reaction, caloric, gas,
        water_id="water", hydrogen_id="hydrogen", oxygen_id="oxygen",
        pressure=ProductPressureBoundary(source_pressure_pa,
            "authored-pressurized-product-boundary; external-pressure-work-unresolved", False),
        evidence=PVBoundaryEvidence("authored-direct-DC-case", "authored-diode-parameters",
            "effective-irradiance-at-cell-plane", "prescribed-cell-temperature",
            "authored-energy-clock", Origin.SYNTHETIC),
        domain=DirectDCDomain(280., 360., 1800., 100., 100., maximum_current_density,
            2e4, maximum_receiver_pressure_pa), faradaic_efficiency=faradaic_efficiency)


def source_stages():
    return (PVStage("sun-1", 100., 130., "authored-energy-clock", 650., 303.15, 298.15,
                    "authored-source-1", Origin.SYNTHETIC),
            PVStage("sun-2", 130., 160., "authored-energy-clock", 950., 313.15, 298.15,
                    "authored-source-2", Origin.SYNTHETIC))


def source_profile():
    """Synthetic three-knot profile for bounded midpoint-stage examples."""
    return PVBoundaryProfile(
        "authored-irradiance-temperature-profile",
        "authored-energy-clock",
        Origin.SYNTHETIC,
        (
            PVBoundarySample(100., 650., 303.15, "profile-knot-1"),
            PVBoundarySample(130., 950., 313.15, "profile-knot-2"),
            PVBoundarySample(160., 700., 308.15, "profile-knot-3"),
        ),
    )


def run_example(model=None, stages=None, *, water_mol=2.):
    model = build_model() if model is None else model
    return model.run(source_stages() if stages is None else stages,
        initial_amounts_mol={"water": water_mol, "hydrogen": .2, "oxygen": .1},
        receiver_volume_m3=.01, receiver_temperature_k=298.15)


def run_profile_example(model=None, *, subdivisions_per_gap=4):
    """Run bounded interpolation with explicit max gap and midpoint resolution."""
    model = build_model() if model is None else model
    stages = source_profile().stages(
        stack_temperature_k=298.15,
        maximum_gap_s=30.,
        subdivisions_per_gap=subdivisions_per_gap,
    )
    return run_example(model, stages)


def main():
    # This entrypoint has deliberately not been run locally.
    trace = run_example(build_model(native_packages="artifacts/native_pvlib_packages"))
    print(STATUS)
    print("H2 mol produced:", trace.final.amounts_mol["hydrogen"]-trace.initial.amounts_mol["hydrogen"])
    print("Pressure support resolved:", trace.pressure_work_resolved)
    print("Required external pressure work:", trace.required_external_pressure_work_j)
    print("Result admission scope:", trace.admission.verification_scope)
    print("No utility availability/continuous feedback/experimental validation is claimed.")


if __name__ == "__main__":
    main()
