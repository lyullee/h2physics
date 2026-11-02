"""Actual native thermal cycle to a bounded existing-stack operating point.

All electrical efficiencies, polarization coefficients and the single-state
reaction energies below are authored software fixtures, not plant measurements.
The native thermal cycle uses CoolProp. No new polarization or fluid EOS is
implemented. This is steady power coupling, not finite water/H2 stock dynamics.
"""

import math

from scipy.optimize import brentq

from h2physics.adapters.thermal_cycles import solve_rankine_cycle
from h2physics.electrochemistry import (
    HydrogenStack,
    OhmicLoss,
    ReactionEnergy,
    StackGeometry,
    SymmetricButlerVolmerLoss,
)


def run_example(cycle=None, *, generator_efficiency=.95, upper_current_density_a_m2=20_000.):
    """Solve the steady cycle, then match its converted shaft power to the stack.

    The upper current density is an explicit assumed operating-domain bound.
    Insufficient admissible stack capacity raises instead of extending that
    bound or discarding power. The caller can supply an already solved cycle.
    """
    if not math.isfinite(generator_efficiency) or not 0 < generator_efficiency <= 1:
        raise ValueError("Declare generator efficiency in (0,1]")
    if not math.isfinite(upper_current_density_a_m2) or upper_current_density_a_m2 <= 0:
        raise ValueError("Declare a finite positive stack current-density bound")
    cycle = solve_rankine_cycle() if cycle is None else cycle
    electrical_power = generator_efficiency*cycle.energy.net_output_w
    if electrical_power <= 0:
        raise ValueError("The supplied solved cycle has no positive net shaft resource")
    temperature = 333.15

    def authored_single_state_energies(temperature_k):
        if not math.isclose(temperature_k, temperature, abs_tol=1e-9, rel_tol=0):
            raise ValueError("Synthetic reaction energies are defined at this one fixture state")
        return ReactionEnergy(237_000.,285_000.,
            "authored-single-state-software-fixture-not-measured-thermochemistry","liquid")

    stack = HydrogenStack(StackGeometry(100,.02,.002016),authored_single_state_energies,
        {"activation":SymmetricButlerVolmerLoss(lambda _:10.,1.),
         "ohmic":OhmicLoss(lambda _:2e-5)})

    def evaluate(current_density):
        return stack.evaluate(current_density,temperature,mode="electrolysis",faradaic_efficiency=1.)

    if evaluate(upper_current_density_a_m2).electric_input_w < electrical_power:
        raise ValueError("Available power exceeds the declared stack operating-current bound")
    current_density = brentq(lambda j:evaluate(j).electric_input_w-electrical_power,
                             0.,upper_current_density_a_m2,xtol=1e-9,rtol=1e-12)
    result = evaluate(current_density)
    generator_loss = cycle.energy.net_output_w-electrical_power
    return {"cycle":cycle,"stack":stack,"stack_result":result,
        "assumption_id":"authored-steady-generator-and-stack-fixtures-not-plant-data",
        "current_density_a_m2":current_density,"generator_efficiency":generator_efficiency,
        "generator_heat_rejection_w":generator_loss,
        "electrical_power_residual_w":electrical_power-result.electric_input_w,
        "shaft_to_reaction_energy_residual_w":cycle.energy.net_output_w-generator_loss
            -result.reaction_enthalpy_rate_w-result.isothermal_heat_rejection_w}


if __name__ == "__main__":
    outputs = run_example()
    print("net shaft output W:",outputs["cycle"].energy.net_output_w)
    print("stack current density A/m2:",outputs["current_density_a_m2"])
    print("hydrogen flow kg/s:",outputs["stack_result"].hydrogen_production_kg_s)
    print("combined power residual W:",outputs["shaft_to_reaction_energy_residual_w"])
