"""Original synthetic finite-solid example; execution is explicitly deferred."""

from h2physics.core import Origin
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
from h2physics.storage.solid_reaction import (
    FiniteSolidReactionReactor,
    SolidReactionEvidence,
    SolidReactionKinetics,
    SolidReactionStep,
)
from h2physics.thermochemical import ThermochemicalInventory


def problem():
    """Build objects only: these fictitious species are not material parameters."""
    species = (
        ChemicalSpecies("fixture-rich", {"Al": 1, "H": 2}, 0.029, "solid:fixture-rich"),
        ChemicalSpecies("fixture-spent", {"Al": 1}, 0.027, "solid:fixture-spent"),
        ChemicalSpecies("H2", {"H": 2}, 0.002, "gas:fixture"),
    )
    caloric = FunctionalMolarEnthalpy(
        species,
        (
            lambda t, p: -1000.0 + 30.0 * (t - 300.0),
            lambda t, p: 18.0 * (t - 300.0),
            lambda t, p: 12.0 * (t - 300.0),
        ),
        "authored-common-formation-reference",
        (200.0, 900.0),
        (1e4, 1e6),
    )
    reaction = StoichiometricReaction("fixture-forward-decomposition", species, (-1, 1, 1))
    kinetics = SolidReactionKinetics(
        reaction,
        lambda state, parameters: (
            parameters["k_per_s"] * state.inventory.amounts_mol["fixture-rich"]
        ),
        "fixture-rate",
        "authored-first-order-numerical-example",
        Origin.SYNTHETIC,
        {"k_per_s": 0.1},
    )
    evidence = SolidReactionEvidence(
        "fixture-reactor",
        "authored-balanced-formulas",
        caloric.basis_id,
        "common-temperature",
        "externally-maintained-absolute-pressure",
        "prescribed-species-takeoff",
        Origin.SYNTHETIC,
    )
    reactor = FiniteSolidReactionReactor(
        caloric, kinetics, evidence, hydrogen_species="H2", mode="decomposition"
    )
    initial = ThermochemicalInventory({"fixture-rich": 2.0}, 300.0, 1e5, caloric.basis_id)
    step = SolidReactionStep(
        "one-second", 0.0, 1.0, "authored-seconds", 500.0, (200.0, 900.0), "authored-command"
    )
    return reactor, initial, (step,)


def run_example():
    reactor, initial, steps = problem()
    return reactor.run(initial, steps)


if __name__ == "__main__":
    raise SystemExit(
        "Execution deferred: import problem()/run_example() in the authorized HPC run."
    )
