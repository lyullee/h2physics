"""Lazy liquid release composition through existing physical owners and graph.

Caller factories declare the spray distribution, flight boundary, finite impact
surface, native pool configuration and optional SLAB conditions. Construction
does not evaluate thermodynamic states or run any native solver.
"""

from collections.abc import Mapping
from types import MappingProxyType

from ..scenarios import OperationalScenario, ScenarioNode, ScenarioOutput, ScenarioValue
from .droplet_transport import flash_initial_liquid_release
from .parcel_impact_chain import impact_population_member
from .parcel_pool_chain import run_deposited_batch_pool, run_parcel_pool_dispersion
from .parcel_population import run_parcel_population


def liquid_release_scenario(*, scenario_id, properties, upstream_state,
                            downstream_pressure_pa, total_release_mass_kg,
                            phase_equilibrium_evidence_id, population_factory,
                            flight_owner_factory, flight_options,
                            distribution_evidence_id, impact_group_id,
                            impact_owner_factory, pool_options_factory,
                            slab_options_factory=None):
    """Build flash -> population -> unit member impact -> pool -> optional SLAB.

    ``population_factory(flash)`` returns explicit population groups;
    ``flight_owner_factory(flash)`` returns the existing flight owner.
    ``impact_owner_factory(population)`` returns the finite surface impact owner.
    ``pool_options_factory(member_impact)`` returns all keyword arguments for
    ``run_deposited_batch_pool`` except step and impact_owner, including the
    actual native config and separate continuation heat owner. Optional
    ``slab_options_factory(pool)`` returns the existing preferred SLAB keywords.
    Every stage output and original failed-stage prefix remains in the shared
    OperationalScenario result/error. Only the explicitly selected unit-count
    group reaches a surface; other group trajectories remain in the population.
    """
    factories = (population_factory, flight_owner_factory, impact_owner_factory,
                 pool_options_factory)
    if any(not callable(factory) for factory in factories):
        raise TypeError("Declare explicit population, flight, impact and pool factories")
    if slab_options_factory is not None and not callable(slab_options_factory):
        raise TypeError("Optional SLAB options factory must be callable")
    if not isinstance(flight_options, Mapping):
        raise TypeError("Flight options must be an explicit Python mapping")
    options = MappingProxyType(dict(flight_options))

    def population_operation(flash):
        flash.__post_init__()
        snapshot = repr(flash)
        owner = flight_owner_factory(flash)
        groups = population_factory(flash)
        flash.__post_init__()
        if repr(flash) != snapshot:
            raise ValueError("Population factories changed the original flash partition")
        result = run_parcel_population(
            flash, owner, groups,
            distribution_evidence_id=distribution_evidence_id, flight_options=options)
        if result.initial_flash is not flash or result.owner is not owner:
            raise ValueError("Population result lost its exact flash and flight parents")
        return result.require_current()

    def impact_operation(population):
        population.require_current()
        owner = impact_owner_factory(population)
        population.require_current()
        return impact_population_member(population, impact_group_id, owner)

    def pool_operation(member):
        member.require_current()
        supplied = pool_options_factory(member)
        member.require_current()
        if not isinstance(supplied, Mapping):
            raise TypeError("Pool options factory must return named Python arguments")
        kwargs = dict(supplied)
        if {"step", "impact_owner"} & kwargs.keys():
            raise ValueError("Original member impact owns its step and impact owner")
        result = run_deposited_batch_pool(
            member.impact_result.steps[0], impact_owner=member.impact_owner, **kwargs)
        member.require_current()
        if (result.initialization.impact_step is not member.impact_result.steps[0]
                or result.initialization.impact_owner is not member.impact_owner):
            raise ValueError("Pool continuation lost its exact impact parents")
        return result

    nodes = [
        ScenarioNode("flash", flash_initial_liquid_release, {
            "properties": ScenarioValue(properties),
            "upstream_state": ScenarioValue(upstream_state),
            "downstream_pressure_pa": ScenarioValue(downstream_pressure_pa),
            "total_release_mass_kg": ScenarioValue(total_release_mass_kg),
            "phase_equilibrium_evidence_id": ScenarioValue(phase_equilibrium_evidence_id),
        }, phase_equilibrium_evidence_id),
        ScenarioNode("population", population_operation, {"flash": ScenarioOutput("flash")},
                     distribution_evidence_id),
        ScenarioNode("impact", impact_operation, {"population": ScenarioOutput("population")},
                     scenario_id+":explicit-member-impact"),
        ScenarioNode("pool", pool_operation, {"member": ScenarioOutput("impact")},
                     scenario_id+":explicit-deposited-stock-pool"),
    ]
    if slab_options_factory is not None:
        def dispersion_operation(pool):
            pool.require_current()
            supplied = slab_options_factory(pool)
            pool.require_current()
            if not isinstance(supplied, Mapping):
                raise TypeError("SLAB options factory must return named Python arguments")
            return run_parcel_pool_dispersion(pool, **dict(supplied))

        nodes.append(ScenarioNode("dispersion", dispersion_operation,
            {"pool": ScenarioOutput("pool")}, scenario_id+":explicit-SLAB-slices"))
    return OperationalScenario(scenario_id, tuple(nodes))
