"""Original finite fuel-cell examples; no execution on import."""


def synthetic_problem(*, water_phase="liquid", hydrogen_id="H2",
                      hydrogen_molar_mass_kg_mol=None,
                      clock_id="authored-seconds", operating_state=None):
    from h2physics.adapters.carrier_conversion import coolprop_carrier_caloric
    from h2physics.adapters.fuel_cell import (
        FiniteFuelCell,
        FuelCellBoundary,
        FuelCellEvidence,
        FuelCellStep,
    )
    from h2physics.constants import FARADAY_C_MOL
    from h2physics.core import Origin
    from h2physics.electrochemistry import HydrogenStack, OhmicLoss, ReactionEnergy, StackGeometry
    from h2physics.reactions import ChemicalSpecies
    from h2physics.thermo.coolprop import CoolPropMolarEnthalpy, CoolPropProperties
    from h2physics.thermochemical import ThermochemicalInventory

    if water_phase not in {"liquid", "vapor"}:
        raise ValueError("Declare liquid or vapor product water")
    operating_temperature = 320.0 if water_phase == "liquid" else 410.0
    temperature_bounds = (280.0, 360.0) if water_phase == "liquid" else (405.0, 430.0)
    h2 = CoolPropProperties("Hydrogen")
    o2 = CoolPropProperties("Oxygen")
    water_fluid = "Water"
    water = CoolPropProperties(water_fluid)
    if hydrogen_molar_mass_kg_mol is None:
        hydrogen_molar_mass_kg_mol = h2.molar_mass_kg_mol
    if abs(h2.molar_mass_kg_mol - hydrogen_molar_mass_kg_mol) > 1e-9 * h2.molar_mass_kg_mol:
        raise ValueError("Fuel-cell H2 mass basis must match the CoolProp Hydrogen fluid")
    species = (
        ChemicalSpecies(hydrogen_id, {"H": 2}, h2.molar_mass_kg_mol, "gas"),
        ChemicalSpecies("O2", {"O": 2}, o2.molar_mass_kg_mol, "gas"),
        ChemicalSpecies(
            "H2O",
            {"H": 2, "O": 1},
            h2.molar_mass_kg_mol + 0.5 * o2.molar_mass_kg_mol,
            "liquid" if water_phase == "liquid" else "vapor",
        ),
    )
    reference_t, reference_p = 298.15, 101325.0
    # NIST Chemistry WebBook: https://webbook.nist.gov/cgi/cbook.cgi?Name=water&cTC=on&cTG=on
    # Standard water formation enthalpies at 298.15 K; offsets align EOS zeros.
    # Both phases share the liquid reference; CoolProp supplies vaporization H.
    formation_water_j_mol = -285830.0
    offsets = (
        -h2.state_pt(reference_p, reference_t).enthalpy_j_kg * h2.molar_mass_kg_mol,
        -o2.state_pt(reference_p, reference_t).enthalpy_j_kg * o2.molar_mass_kg_mol,
        formation_water_j_mol - water.state_pt(reference_p, reference_t).enthalpy_j_kg * water.molar_mass_kg_mol,
    )
    provider = CoolPropMolarEnthalpy(
        species, ("Hydrogen", "Oxygen", water_fluid), offsets,
        basis_id="CoolProp-state-enthalpy+NIST-formation-reference:" + water_phase,
        temperature_bounds_k=temperature_bounds, pressure_bounds_pa=(5e4, 1.1e5),
    )
    source = coolprop_carrier_caloric(
        provider,
        phase_reference_id="authored-common-phase-formation-reference:" + water_phase,
        hydrogen_partition_id="CoolProp-Hydrogen-normal-frozen-spin",
        source_id="CoolProp-HEOS+NIST-water-formation-reference",
        origin=Origin.PREDICTED,
    )

    def thermochemistry(t, basis=provider.basis_id, phase=water_phase):
        h = provider.enthalpies_j_mol(t, 101325.0)
        reaction_h = h[0] + h[1] / 2.0 - h[2]
        # Gibbs energy is an explicit illustrative input; state enthalpies come from CoolProp.
        return ReactionEnergy(2 * FARADAY_C_MOL, reaction_h, basis, phase)

    stack = HydrogenStack(
        StackGeometry(3, 0.02, hydrogen_molar_mass_kg_mol),
        thermochemistry,
        {"authored-ohmic": OhmicLoss(lambda t: 0.0005)},
    )
    boundary = FuelCellBoundary(
        101325.0,
        water_phase,
        temperature_bounds,
        500.0,
        1e-7,
        "authored-fixed-activities-not-inventory-derived",
        "explicit-temperature-thermostat",
        "externally-maintained-absolute-pressure",
        "process-frame",
        "hydrogen-inlet",
        "oxidant-inlet",
        "component-outlet",
    )
    evidence = FuelCellEvidence(
        "authored-finite-fuel-cell",
        clock_id,
        "stack-region",
        "authored-ohmic-not-device-fit",
        "authored-G-and-common-H",
        "imposed-component-takeoff",
        "explicit-etaF-one-no-side-reaction",
        Origin.SYNTHETIC,
    )
    model = FiniteFuelCell(stack, source, boundary, evidence, hydrogen_id=hydrogen_id)
    initial = ThermochemicalInventory(
        {hydrogen_id: 0.01, "O2": 0.007, "H2O": 0.001}, operating_temperature, boundary.pressure_pa, provider.basis_id
    )
    steps = (
        FuelCellStep(
            "operate", 0.0, 10.0, evidence.clock_id, operating_temperature, 200.0, 1.0,
            "authored-current-command", operating_state=operating_state,
        ),
    )
    return model, initial, steps


def native_gas_problem():
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_caloric import (
        CaloricSpeciesMapping,
        CanteraMultiphaseMolarEnthalpy,
    )
    from h2physics.adapters.cantera_multiphase import EquilibriumPhase
    from h2physics.adapters.carrier_conversion import CarrierCaloricSource
    from h2physics.adapters.fuel_cell import (
        FiniteFuelCell,
        FuelCellBoundary,
        FuelCellEvidence,
        FuelCellStep,
    )
    from h2physics.core import Origin
    from h2physics.electrochemistry import HydrogenStack, OhmicLoss, ReactionEnergy, StackGeometry
    from h2physics.thermochemical import ThermochemicalInventory

    raw = (Path(ct.__file__).parent / "data" / "gri30.yaml").read_bytes()
    text = raw.decode()
    basis = MechanismBasis(
        "installed-GRI-fuel-cell-calorimetry",
        hashlib.sha256(raw).hexdigest(),
        "BSD-3-Clause; existing native data rights",
        ("https://cantera.org/3.2/python/thermo.html",),
        500.0,
        900.0,
        5e4,
        2e5,
    )
    reference = "native-GRI-common-formation-reference"
    provider = CanteraMultiphaseMolarEnthalpy(
        (
            EquilibriumPhase(
                "gas",
                "gas",
                lambda: ct.Solution(yaml=text, name="gri30"),
                basis,
                reference,
                "native-H2-spin-unresolved-frozen",
            ),
        ),
        tuple(CaloricSpeciesMapping("gas", name, name) for name in ("H2", "O2", "H2O")),
    )

    def probe(provider=provider):
        provider._require_definitions()
        return (
            vars(provider),
            provider._require_definitions,
            getattr(provider._require_definitions, "__self__", None),
            tuple(
                (vars(gas), gas.enthalpies_j_mol, getattr(gas.enthalpies_j_mol, "__self__", None))
                for gas in provider.native_gas_providers.values()
            ),
        )

    source = CarrierCaloricSource(
        provider,
        phase_reference_id=reference,
        hydrogen_partition_id="native-H2-spin-unresolved-frozen",
        source_id="installed-GRI-native-caloric",
        origin=Origin.PREDICTED,
        definition_probe=probe,
        native_objects=(*provider.source_phases, *provider.owned_phases),
    )
    native = provider.owned_phases[0]
    indices = tuple(native.species_index(name) for name in ("H2", "O2", "H2O"))
    pressure = 101325.0

    def thermochemistry(
        t,
        source=source,
        native=native,
        indices=indices,
        pressure=pressure,
        fractions=(0.5, 0.25, 0.25),
    ):
        source.require_current()
        h = source.provider.enthalpies_j_mol(t, pressure)
        # Explicit held gas activities at each callback, not the bulk finite
        # inventory's evolving composition or an inferred Nernst correction.
        native.TPX = t, pressure, dict(zip(("H2", "O2", "H2O"), fractions, strict=True))
        mu = native.chemical_potentials
        g = (mu[indices[0]] + 0.5 * mu[indices[1]] - mu[indices[2]]) / 1000.0
        return ReactionEnergy(g, h[0] + 0.5 * h[1] - h[2], source.provider.basis_id, "vapor")

    stack = HydrogenStack(
        StackGeometry(6, 0.012, provider.species[0].molar_mass_kg_mol),
        thermochemistry,
        {"authored-ohmic": OhmicLoss(lambda t: 1.7e-5)},
    )
    boundary = FuelCellBoundary(
        pressure,
        "vapor",
        (500.0, 900.0),
        1000.0,
        1e-6,
        "explicit-held-0.5H2-0.25O2-0.25H2O-activities",
        "explicit-gas-thermostat",
        "externally-maintained-pressure",
        "native-process-frame",
        "H2-in",
        "O2-in",
        "component-out",
    )
    evidence = FuelCellEvidence(
        "authored-native-gas-fuel-cell",
        "authored-seconds",
        "gas-stack-region",
        "authored-ohmic-no-device-validation",
        "actual-native-H-and-mu-fixed-activity",
        "imposed-component-takeoff",
        "explicit-etaF-one",
        Origin.SYNTHETIC,
    )
    model = FiniteFuelCell(stack, source, boundary, evidence)
    initial = ThermochemicalInventory(
        {"H2": 0.012, "O2": 0.008, "H2O": 0.002}, 650.0, pressure, provider.basis_id
    )
    steps = (
        FuelCellStep(
            "native-operate", 0.0, 20.0, evidence.clock_id, 650.0, 240.0, 1.0, "authored-current"
        ),
        FuelCellStep(
            "takeoff-idle",
            20.0,
            30.0,
            evidence.clock_id,
            650.0,
            0.0,
            1.0,
            "explicit-zero-current",
            pre_withdrawal_mol={"H2O": 0.001},
        ),
    )
    return model, initial, steps


def run_example():
    model, initial, steps = synthetic_problem()
    return model.run(initial, steps)
