"""Authored conditional crack growth example; not executed locally.

Run only in an explicitly prepared validation environment. The coefficients and
geometry below are synthetic verification inputs, not hydrogen material data.
"""

import math

from h2physics.adapters.fracture_fatigue import (
    CrackGeometryCallback,
    CrackStopConditions,
    FractureIntegrationSettings,
    FractureMaterialDomain,
    HelprFatigueLaw,
    HelprLawSelection,
    HydrogenCrackEnvironment,
    LoadCycleBlock,
    LoadCycleHistory,
    ModeIStressIntensity,
    integrate_fatigue_crack,
)
from h2physics.core import Origin


def authored_case(*, cycles=5000.0, stop_size_m=0.0015, toughness_pa_sqrt_m=8e6):
    """Build metadata/callbacks only; does not import or execute HELPR."""
    environment = HydrogenCrackEnvironment(
        8e6,
        4e6,
        293.15,
        1.0,
        8e6,
        "authored-supplied-fugacity-not-an-EOS-evaluation",
        "synthetic-gas-boundary",
        Origin.SYNTHETIC,
    )
    block = LoadCycleBlock(
        "ordered-amplitude", 0.0, cycles, 1000.0, 1000.0 + cycles / 0.5, 12e6, 42e6, environment
    )
    history = LoadCycleHistory(
        (block,),
        "fatigue-cycle-coordinate",
        "physical-operation-clock",
        "supplied-nominal-tensile-stress",
        "authored-ordered-cycles-not-a-histogram",
        "synthetic-fracture-fixture",
        Origin.SYNTHETIC,
    )

    def infinite_plate(crack_m, load):
        # Independently authored basic LEFM geometry, not a fitted component Y.
        factor = math.sqrt(math.pi * crack_m)
        return ModeIStressIntensity(
            load.minimum_stress_pa * factor, load.maximum_stress_pa * factor
        )

    geometry = CrackGeometryCallback(
        "authored-infinite-plate",
        infinite_plate,
        1e-5,
        0.002,
        0.01,
        "analytic-infinite-plate;not-a-vessel",
        "bounded-numerical-event-extension",
    )
    material = FractureMaterialDomain(
        (0.0, 10e6),
        (290.0, 300.0),
        (0.0, 10e6),
        (0.0, 0.9),
        (0.1, 1.0),
        (1.0, 15e6),
        30e6,
        "authored-not-an-alloy",
        "synthetic-m2-curve",
        "no-measured-hydrogen-qualification",
        "authored-LEFM-small-scale-yielding",
        "explicit-trial-range-not-physical-extrapolation",
        Origin.SYNTHETIC,
    )
    conditions = CrackStopConditions(
        stop_size_m,
        toughness_pa_sqrt_m,
        0.0,
        "authored-size-and-Kmax-boundaries",
        "zero-range-arrest-only",
        False,
    )
    selection = HelprLawSelection(
        "paris_law",
        "synthetic-coefficient-not-hydrogen-correction",
        paris_coefficient_si=2e-20,
        paris_exponent=2.0,
    )
    return history, geometry, material, conditions, selection


def run_example():
    """Actual native law + SciPy run; invocation is deferred, never done at import."""
    history, geometry, material, conditions, selection = authored_case()
    result = integrate_fatigue_crack(
        HelprFatigueLaw(selection),
        history,
        geometry,
        material,
        conditions,
        initial_crack_m=0.0007,
        settings=FractureIntegrationSettings(maximum_cycle_step=20.0),
    )
    # Actual native objects and numerical results are available for deep Python use.
    return result, result.native_owners[0].growth, result.native_solutions[0]


if __name__ == "__main__":
    result, native_growth, native_ode = run_example()
    print(result.termination, result.snapshots[-1].cycle, result.snapshots[-1].crack_size_m)
