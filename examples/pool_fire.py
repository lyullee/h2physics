"""Authored finite pool-fire reference. Not executed locally."""

import sys
from pathlib import Path

from h2physics.adapters.pool_fire import (
    DeclaredIgnition,
    ExternalConditioningBudget,
    FinitePoolFire,
    GroundVerticalReceptor,
    H2CombustionReference,
    PoolFireNative,
    PoolFireSeed,
    PoolFireStage,
)
from h2physics.core import Origin
from h2physics.reactions import ChemicalSpecies, StoichiometricReaction
from h2physics.release import SourceLocation

STATUS = "implemented_unverified"


def build_model(*, native_packages=None, seed=None):
    if native_packages is not None:
        path = str(Path(native_packages).resolve())
        if path not in sys.path:
            sys.path.append(path)
    from h2physics.storage.finite_hydride import HydrideGasThermodynamics
    from h2physics.thermo import CoolPropProperties

    native = PoolFireNative.from_installed()
    properties = CoolPropProperties("Hydrogen")
    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    location = SourceLocation("authored-pool", "pool-fire-clock", "authored-ground-ENU",
                              (0., 0., 0.), (0., 0., 1.))
    if seed is None:
        seed = PoolFireSeed(100., .02, .04, location,
            properties.saturated(101325., 0.), properties.saturated(101325., 1.),
            (properties, gas), "authored-fixed-normal-LH2-stock", Origin.SYNTHETIC)
    reference = H2CombustionReference(1.17e8,
        properties.state_pt(seed.liquid_state.pressure_pa, 298.15),
        "authored-LHV-energy-scale-not-qualified", "authored-H2-scope-not-experimental-validation",
        "authored-finite-O2-at-reference-temperature", Origin.SYNTHETIC, "vapor", 1.)
    mh2, oxygen_atom_mass = gas.molar_mass_kg_mol, .0159994
    species = (ChemicalSpecies("H2-vapor", {"H": 2}, mh2, "gas"),
        ChemicalSpecies("O2", {"O": 2}, 2*oxygen_atom_mass, "gas"),
        ChemicalSpecies("water-vapor", {"H": 2, "O": 1}, mh2+oxygen_atom_mass, "vapor"))
    reaction = StoichiometricReaction("complete-H2-combustion-reference", species, (-1., -.5, 1.))
    return FinitePoolFire(native, seed, reference, reaction,
                         hydrogen_id="H2-vapor", oxygen_id="O2", water_id="water-vapor")


def stages(model):
    start, clock = model.seed.time_s, model.seed.location.clock_id
    return (PoolFireStage("declared-established-burning", start, start+30., clock,
        .05, "authored-H2-net-consumption-flux-not-calibrated", 1.,
        "authored-ground-tangent-uniform-sphere-proxy", .18, .55,
        "authored-radiant-convective-export-partition", Origin.SYNTHETIC),)


def receptors(model):
    location = model.seed.location
    x, y, z = location.position_m
    return (GroundVerticalReceptor("front-3m", location.clock_id, location.coordinate_frame_id,
        (x+3., y, z), (-1., 0., 0.), .9, "authored-small-vertical-receptor",
        "authored-transmissivity-not-atmosphere-fit", Origin.SYNTHETIC),)


def run_example(model=None, *, schedule=None, target_receptors=None,
                conditioning_energy_j=2e5, conditioning_power_w=2e4, oxygen_mol=10.):
    model = build_model() if model is None else model
    return model.run(stages(model) if schedule is None else schedule,
        receptors(model) if target_receptors is None else target_receptors,
        ignition=DeclaredIgnition(model.seed.time_s, model.seed.location.clock_id,
            "authored-explicit-ignition-no-probability", Origin.SYNTHETIC),
        conditioning=ExternalConditioningBudget(model.seed.location.clock_id,
            conditioning_energy_j, conditioning_power_w, "authored-finite-external-conditioner",
            Origin.SYNTHETIC), initial_oxygen_mol=oxygen_mol)


def build_native_preignition_seed():
    """Deferred actual native pool calculation, never called at import."""
    import importlib.metadata

    from dynamiclh2poolx import (
        DeclaredInflow,
        DynamicPoolConfig,
        ShallowLayerNumerics,
        SolidSemiInfiniteSurface,
        run_dynamic_pool,
    )

    from h2physics.adapters.pool import DeclaredGroundInflow, NativeDynamicPool, PoolTolerances
    from h2physics.thermo import CoolPropProperties

    if importlib.metadata.version("dynamiclh2poolx") != "0.2.0rc2":
        raise ValueError("Install the existing reviewed optional native pool")
    properties = CoolPropProperties("Hydrogen")
    ground = SourceLocation("authored-preignition-ground", "pool-fire-clock",
        "authored-ground-ENU", (0., 0., 0.), (0., 0., 1.))
    vapor = SourceLocation("authored-preignition-vapor", "pool-fire-clock",
        "authored-ground-ENU", (0., 0., 0.), (0., 0., 1.))
    inflow = DeclaredGroundInflow(DeclaredInflow((0., .5), (.02, 0.)), ground,
        properties.saturated(101325., 0.), 100., 101., Origin.SYNTHETIC,
        "authored-finite-native-preignition-source", "isolation")
    config = DynamicPoolConfig(surface=SolidSemiInfiniteSurface("authored-substrate", .16, 7e-7, 80.),
        numerics=ShallowLayerNumerics(domain_radius_m=1.5, source_radius_m=.12,
            radial_step_m=.02, maximum_time_step_s=.005), ambient_pressure_Pa=101325.)
    bridge = NativeDynamicPool(run_dynamic_pool, properties,
        engine_id="DynamicLH2PoolX:0.2.0rc2:6a700e8e183039bbb81803bacc416f6c9117ed71",
        tolerances=PoolTolerances(event_clock_roundoff_s=1e-10))
    run = bridge.run(config, inflow, output_times_s=(100., 100.25, 100.5, 101.), vapor_location=vapor)
    return PoolFireSeed.from_native_pool(run, evidence_id="native-final-preignition-stock-to-fire")


def main():
    trace = run_example(build_model(native_packages="artifacts/native_risk_packages"))
    print(STATUS)
    print("Fuel consumed kg:", trace.fuel_to_flame.total_mass_kg)
    print("Remaining LH2 kg:", trace.steps[-1].remaining_liquid_kg)
    print("No fire feedback, predicted flame shape or dispersion validation is claimed.")


if __name__ == "__main__":
    main()
