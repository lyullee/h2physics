"""Original synthetic microbial/native cathode fixture; not executed locally."""

import hashlib

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.microbial_cell import (
    CanteraMicrobialCathode,
    CathodeEvidence,
    FiniteMicrobialCell,
    MicrobialCellEvidence,
    MicrobialCellStage,
    MicrobialKinetics,
    MicrobialRates,
)
from h2physics.core import Origin
from h2physics.electrochemistry import OhmicLoss, StackGeometry
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
from h2physics.thermochemical import ThermochemicalInventory

# Authored constant-cp/electrochemical verification inputs, not a measured
# electrode mechanism, liquid-water database or microbial performance model.
NATIVE_YAML = """
units: {length: m, time: s, quantity: kmol, activation-energy: J/kmol}
phases:
- name: product
  thermo: ideal-gas
  species: [H2]
  state: {T: 300 K, P: 100000 Pa, X: {H2: 1}}
- name: broth-boundary
  thermo: ideal-condensed
  species: [water, Hplus, Clminus]
  standard-concentration-basis: unity
  state: {T: 300 K, P: 100000 Pa, X: {water: 0.8, Hplus: 0.1, Clminus: 0.1}}
- name: conductor
  thermo: electron-cloud
  species: [electron]
  density: 1 kg/m^3
  state: {T: 300 K, P: 100000 Pa, X: {electron: 1}}
- name: cathode
  thermo: ideal-surface
  adjacent-phases: [product, broth-boundary, conductor]
  species: [site]
  kinetics: surface
  reactions: all
  site-density: 1.0e-5
  state: {T: 300 K, coverages: {site: 1}}
species:
- name: H2
  composition: {H: 2}
  thermo: {model: constant-cp, T0: 300 K, h0: 0 J/kmol, s0: 0 J/kmol/K, cp0: 29000 J/kmol/K}
- name: water
  composition: {H: 2, O: 1}
  thermo: {model: constant-cp, T0: 300 K, h0: -1000000 J/kmol, s0: 0 J/kmol/K, cp0: 75000 J/kmol/K}
  equation-of-state: {model: constant-volume, molar-volume: 0.018 m^3/kmol}
- name: Hplus
  composition: {H: 1, E: -1}
  thermo: {model: constant-cp, T0: 300 K, h0: 0 J/kmol, s0: 0 J/kmol/K, cp0: 20000 J/kmol/K}
  equation-of-state: {model: constant-volume, molar-volume: 0.001 m^3/kmol}
- name: Clminus
  composition: {Cl: 1, E: 1}
  thermo: {model: constant-cp, T0: 300 K, h0: 0 J/kmol, s0: 0 J/kmol/K, cp0: 20000 J/kmol/K}
  equation-of-state: {model: constant-volume, molar-volume: 0.001 m^3/kmol}
- name: electron
  composition: {E: 1}
  thermo: {model: constant-cp, T0: 300 K, h0: 0 J/kmol, s0: 0 J/kmol/K, cp0: 0 J/kmol/K}
- name: site
  composition: {}
  thermo: {model: constant-cp, T0: 300 K, h0: 0 J/kmol, s0: 0 J/kmol/K, cp0: 0 J/kmol/K}
reactions:
- equation: 2 Hplus + 2 electron <=> H2
  rate-constant: {A: 1.0e-9, b: 0, Ea: 0}
  exchange-current-density-formulation: true
  beta: 0.5
"""


def build_problem(*, catabolic_parameter=1e-4, growth_parameter=2e-5):
    """Build native objects only on an explicit future HPC call."""
    import cantera as ct

    reference = "authored-aqueous-and-native-H2-common-formation-reference"
    basis = MechanismBasis(
        "authored-native-MEC-cathode",
        hashlib.sha256(NATIVE_YAML.encode()).hexdigest(),
        "original-host-fixture; Cantera BSD-3-Clause",
        ("https://cantera.org/3.2/python/kinetics.html",),
        280.0,
        330.0,
        5e4,
        2e5,
    )
    electrode = CanteraMicrobialCathode(
        NATIVE_YAML,
        "cathode",
        gas_phase="product",
        electrolyte_phase="broth-boundary",
        electron_phase="conductor",
        hydrogen_species="H2",
        electron_species="electron",
        proton_species="Hplus",
        evidence=CathodeEvidence(
            basis,
            "authored-common-electrode-reference",
            "authored-fixed-electroneutral-activity-boundary",
            "authored-native-rate-not-a-material-fit",
            reference,
            Origin.SYNTHETIC,
        ),
    )
    weights = {e: ct.Element(e).weight / 1000.0 for e in ("C", "H", "O", "N")}

    def species(name, formula, phase):
        return ChemicalSpecies(
            name, formula, sum(weights[e] * n for e, n in formula.items()), phase
        )

    h2_mass = electrode.phases[0].molecular_weights[0] / 1000.0
    items = (
        species("substrate", {"C": 1, "H": 2, "O": 1}, "aqueous"),
        species("water", {"H": 2, "O": 1}, "liquid"),
        species("CO2", {"C": 1, "O": 2}, "aqueous"),
        ChemicalSpecies("hydrogen", {"H": 2}, h2_mass, "gas"),
        species("ammonia", {"N": 1, "H": 3}, "aqueous"),
        species("biomass", {"C": 5, "H": 7, "O": 2, "N": 1}, "biomass:dry-formula-unit"),
    )
    catabolism = StoichiometricReaction("authored-CH2O-water-to-H2", items, (-1, -1, 1, 2, 0, 0))
    growth = StoichiometricReaction(
        "authored-balanced-biomass-synthesis", items, (-5, 3, 0, 0, -1, 1)
    )
    offsets = (-10000.0, -1000.0, -25000.0, 0.0, -3000.0, -45000.0)
    capacities = (30.0, 75.0, 35.0, 29.0, 30.0, 100.0)
    functions = tuple(
        lambda t, p, h=h, cp=cp: h + cp * (t - 300.0)
        for h, cp in zip(offsets, capacities, strict=True)
    )
    caloric = FunctionalMolarEnthalpy(items, functions, reference, (280.0, 330.0), (5e4, 2e5))

    def rates(state, parameters):
        n = state.inventory.amounts_mol
        return MicrobialRates(
            parameters["catabolic_m3_per_mol_biomass_s"]
            * n.get("substrate", 0.0)
            * n.get("biomass", 0.0)
            / state.liquid_volume_m3,
            parameters["growth_per_s"] * n.get("biomass", 0.0),
        )

    kinetics = MicrobialKinetics(
        rates,
        "authored-mass-action-microbial-fixture",
        "not-qualified-organism-or-broth-kinetics",
        Origin.SYNTHETIC,
        {"catabolic_m3_per_mol_biomass_s": catabolic_parameter, "growth_per_s": growth_parameter},
        (280.0, 330.0),
        (0.0, 1000.0),
        (0.0, 1000.0),
    )
    evidence = MicrobialCellEvidence(
        "authored-finite-MEC",
        "authored-element-balanced-net-reactions",
        "authored-electron-equivalents; no-COD-to-mass-conversion",
        reference,
        "authored-common-electrode-reference",
        "prescribed-anode-potential-not-a-bioanode-law",
        "fixed-native-broth-activities-no-pH-dynamics",
        "isothermal-fixed-P-no-utility-solution",
        "membrane-ohmic-only; excludes-native-cathode-loss",
        "authored-MEC-clock",
        Origin.SYNTHETIC,
    )
    model = FiniteMicrobialCell(
        electrode,
        catabolism,
        growth,
        kinetics,
        caloric,
        StackGeometry(1, 0.01, h2_mass),
        evidence,
        substrate_id="substrate",
        biomass_id="biomass",
        hydrogen_id="hydrogen",
        liquid_volume_m3=0.001,
        electron_equivalents_mol_per_mol={
            "substrate": 4.0,
            "water": 0.0,
            "CO2": 0.0,
            "hydrogen": 2.0,
            "ammonia": 0.0,
            "biomass": 20.0,
        },
        noncathode_losses={"authored-membrane-ohmic": OhmicLoss(lambda t: 0.002)},
    )
    initial = ThermochemicalInventory(
        {
            "substrate": 0.01,
            "water": 1.0,
            "CO2": 0.001,
            "hydrogen": 1e-4,
            "ammonia": 0.01,
            "biomass": 1e-5,
        },
        300.0,
        1e5,
        reference,
    )
    compositions = {
        "product": {"H2": 1.0},
        "broth-boundary": {"water": 0.8, "Hplus": 0.1, "Clminus": 0.1},
        "conductor": {"electron": 1.0},
    }
    stages = tuple(
        MicrobialCellStage(
            "stage-" + str(i),
            float(i),
            float(i + 1),
            "authored-MEC-clock",
            0.2,
            0.0,
            (-1.0, 1.0),
            compositions,
            "authored-explicit-cathode-boundary",
            True,
        )
        for i in range(2)
    )
    return model, initial, stages


def run_example():
    model, initial, stages = build_problem()
    trace = model.run(initial, stages)
    # Actual StackGeometry and producer admission remain on the original trace.
    # This checks recorded identities/content only; it does not repeat a solve.
    model.verify_result(trace)
    return trace


if __name__ == "__main__":
    raise SystemExit(
        "Scientific execution deferred to the authorized HPC microbial-cell entrypoints."
    )
