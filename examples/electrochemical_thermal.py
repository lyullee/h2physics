"""Customizable finite thermal wrapper around the shared electrochemical stack."""

from h2physics.electrochemical_thermal import (
    FiniteThermalStack,
    ThermalStackBoundary,
    ThermalStackStage,
)
from h2physics.electrochemistry import (
    HydrogenStack,
    OhmicLoss,
    ReactionEnergy,
    StackGeometry,
    SymmetricButlerVolmerLoss,
)


def build_model(*, cells=40, area_m2=0.02, heat_capacity_j_k=12_000.0,
                conductance_w_k=45.0):
    """Build an authored example; replace every callback with apparatus data."""
    stack = HydrogenStack(
        StackGeometry(cells, area_m2, 0.00201588),
        lambda temperature_k: ReactionEnergy(
            228_500.0, 241_800.0, "authored:vapor-water", "vapor"
        ),
        {
            "activation": SymmetricButlerVolmerLoss(lambda temperature_k: 2_000.0, 1.0),
            "ohmic": OhmicLoss(lambda temperature_k: 2.0e-5),
        },
    )
    return FiniteThermalStack(stack, ThermalStackBoundary(
        heat_capacity_j_k=heat_capacity_j_k,
        conductance_w_k=lambda stack_k, coolant_k: conductance_w_k,
        temperature_bounds_k=(273.15, 373.15),
        reference_id="authored:example-stack-thermal-mass",
        coolant_boundary_id="authored:example-held-coolant",
    ))


def run_example(model=None):
    model = model or build_model()
    stages = (
        ThermalStackStage("startup", 0.0, 120.0, 6_000.0, 298.15, "electrolysis"),
        ThermalStackStage("production", 120.0, 600.0, 10_000.0, 303.15,
                          "electrolysis"),
    )
    return model.run(298.15, stages)


if __name__ == "__main__":
    result = run_example()
    print(result.final_temperature_k, result.energy_residual_j)
