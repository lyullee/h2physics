"""Authored finite carrier examples; no work runs on import.

The liquid example is a synthetic formula/caloric fixture, not measured LOHC
properties. The native gas example is prescribed ammonia calorimetry, not a
catalyst, equilibrium-conversion or plant-performance prediction.
"""


def liquid_problem(*, elemental_reference_shift=0.0):
    from h2physics.adapters.carrier_conversion import (
        CarrierProcessEvidence,
        FiniteCarrierConversion,
        functional_carrier_caloric,
        lohc_pathway,
    )
    from h2physics.core import Origin
    from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy
    from h2physics.thermochemical import (
        PrescribedConversion,
        ThermochemicalInventory,
        ThermochemicalStage,
    )

    # Original hypothetical C/H/O bookkeeping species; no molecular stability
    # or real liquid heat-capacity/formation-enthalpy data are claimed.
    species = (
        ChemicalSpecies("rich", {"C": 8, "H": 18, "O": 1}, 0.130, "liquid:authored-rich"),
        ChemicalSpecies("lean", {"C": 8, "H": 12, "O": 1}, 0.124, "liquid:authored-lean"),
        ChemicalSpecies("H2", {"H": 2}, 0.002, "gas:authored-common-reference"),
    )
    shifts = tuple(
        elemental_reference_shift
        * (
            2 * item.elements.get("C", 0)
            + 3 * item.elements.get("H", 0)
            - item.elements.get("O", 0)
        )
        for item in species
    )
    functions = tuple(
        lambda t, p, h=h + shift, cp=cp: h + cp * (t - 300.0)
        for h, shift, cp in zip((-19000.0, -1000.0, 0.0), shifts, (100.0, 70.0, 10.0), strict=True)
    )
    provider = FunctionalMolarEnthalpy(
        species,
        functions,
        f"authored-liquid-carrier:elemental-shift={elemental_reference_shift}",
        (250.0, 650.0),
        (2e4, 5e5),
    )
    reference = "authored-liquid-and-gas-common-formation-reference"
    source = functional_carrier_caloric(
        provider,
        phase_reference_id=reference,
        hydrogen_partition_id="authored-frozen-unspecified-spin-no-conversion",
        source_id="authored-liquid-constant-cp-not-measurement",
        origin=Origin.SYNTHETIC,
    )
    pathway = lohc_pathway(
        species,
        rich_id="rich",
        lean_id="lean",
        hydrogen_id="H2",
        hydrogen_per_carrier=3.0,
        identifier="authored-liquid-rich-to-lean",
        phase_reference_id=reference,
        source_id="authored-balanced-formulas",
        origin=Origin.SYNTHETIC,
    )
    evidence = CarrierProcessEvidence(
        "authored-liquid-packet-process",
        "authored-seconds",
        "carrier-reactor-region",
        reference,
        "authored-prescribed-extent",
        "caller-maintained-constant-P-and-stage-T",
        "authored-component-takeoff-no-separator",
        Origin.SYNTHETIC,
    )
    model = FiniteCarrierConversion(pathway, source, evidence)
    initial = ThermochemicalInventory(
        {"rich": 1.7, "lean": 0.2, "H2": 0.4}, 300.0, 101325.0, provider.basis_id
    )
    stage = ThermochemicalStage(
        "convert",
        0.0,
        12.0,
        evidence.clock_id,
        420.0,
        (PrescribedConversion(pathway.reaction, 0.6, "authored-extent-not-rate"),),
        "authored-isobaric-conditioning-and-conversion",
    )
    return model, initial, (stage,)


def ammonia_problem():
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.carrier_conversion import (
        CarrierProcessEvidence,
        FiniteCarrierConversion,
        ammonia_pathway,
        native_ammonia_caloric,
    )
    from h2physics.core import Origin
    from h2physics.thermochemical import (
        PrescribedConversion,
        ThermochemicalInventory,
        ThermochemicalStage,
    )

    mechanism = Path(ct.__file__).parent / "data" / "gri30.yaml"
    raw = mechanism.read_bytes()
    text = raw.decode("utf-8")
    basis = MechanismBasis(
        "installed-gri30-native-ammonia-calorimetry",
        hashlib.sha256(raw).hexdigest(),
        "BSD-3-Clause; installed Cantera data provenance",
        ("https://cantera.org/3.2/python/thermo.html",),
        300.0,
        3500.0,
        1e4,
        1e6,
    )
    reference = "installed-GRI-species-common-formation-reference"
    source = native_ammonia_caloric(
        lambda: ct.Solution(yaml=text, name="gri30"),
        basis,
        phase_reference_id=reference,
        hydrogen_partition_id="native-H2-spin-unresolved-frozen",
        source_id="installed-gri30-native-fits-not-catalyst-data",
        origin=Origin.PREDICTED,
    )
    pathway = ammonia_pathway(
        source.provider.species,
        identifier="prescribed-NH3-cracking",
        phase_reference_id=reference,
        source_id="balanced-2NH3-N2-3H2",
        origin=Origin.SYNTHETIC,
    )
    evidence = CarrierProcessEvidence(
        "authored-native-ammonia-packet",
        "authored-seconds",
        "ammonia-process-region",
        reference,
        "authored-extent-no-equilibrium-claim",
        "caller-maintained-constant-P-temperature",
        "component-takeoff-no-purity-claim",
        Origin.SYNTHETIC,
    )
    model = FiniteCarrierConversion(pathway, source, evidence)
    initial = ThermochemicalInventory(
        {"NH3": 1.3, "N2": 0.2, "H2": 0.09}, 650.0, 101325.0, source.provider.basis_id
    )
    stages = (
        ThermochemicalStage(
            "convert",
            0.0,
            5.0,
            evidence.clock_id,
            850.0,
            (PrescribedConversion(pathway.reaction, 0.3, "authored-extent"),),
            "authored-heating",
        ),
        ThermochemicalStage(
            "takeoff-cool",
            5.0,
            8.0,
            evidence.clock_id,
            600.0,
            (),
            "imposed-component-takeoff-and-cooling",
            pre_withdrawal_mol={"H2": 0.4, "N2": 0.1},
        ),
    )
    return model, initial, stages


def run_liquid_example():
    model, initial, stages = liquid_problem()
    return model.run(initial, stages)


def run_ammonia_example():
    model, initial, stages = ammonia_problem()
    result = model.run(initial, stages)
    packet = model.withdrawal(
        result,
        1,
        boundary_id="imposed-component-outlet",
        frame_id="authored-process-frame",
        evidence_id="caller-takeoff-operation",
    )
    return result, packet
