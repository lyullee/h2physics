"""Deferred unit-count population contact composition."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="population-unit-member-impact-chain", profile="droplet-impact",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("original unit-count population ground event reaches existing impact owner",
                    "clock/frame and finite wall contact preserve original trajectory identity",
                    "multi-count representative cannot multiply finite-wall impact",
                    "detached impact bridge receipt rejected")),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.droplet_impact import build_model
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
        flash_initial_liquid_release,
    )
    from h2physics.adapters.parcel_impact_chain import (
        PopulationImpactError,
        impact_population_member,
    )
    from h2physics.adapters.parcel_population import ParcelPopulationGroup, run_parcel_population

    impact_owner = build_model()
    properties = impact_owner.properties
    flash = flash_initial_liquid_release(
        properties, properties.saturated(.8e6, 0.), downstream_pressure_pa=101325.,
        total_release_mass_kg=1e-6, phase_equilibrium_evidence_id="authored-PH-partition")
    location = impact_owner.patch.location
    boundary = ParcelBoundary(location.clock_id, location.coordinate_frame_id,
        "authored-fixed-carrier", .01, 1e-5, (0., 0., -1.), (0., 0., 0.), 1e5, 1., .002, .01)
    flight = SaturatedParcelFlight(properties, 101325., boundary,
        lambda state: BoilingHeat(0., "authored-adiabatic-flight"),
        force_approximation_evidence_id="authored-zero-relative-speed")
    options = dict(start_s=100., end_s=102., residual_mass_floor_kg=1e-10,
        maximum_step_s=.01, relative_tolerance=1e-10,
        absolute_tolerances=(1e-12,)*17, ground_z_m=0.)
    group = ParcelPopulationGroup("single", 1, flash.liquid_mass_kg,
        (0., 0., 1.), (0., 0., -1.), "authored-single-parcel")
    population = run_parcel_population(flash, flight, (group,),
        distribution_evidence_id="authored-distribution", flight_options=options)
    receipt = impact_population_member(population, "single", impact_owner)
    step = receipt.impact_result.steps[0]
    assert step.context.incident_trace is population.groups_and_traces[0][1]
    assert step.context.incident.time_s == population.groups_and_traces[0][1].states[-1].time_s
    receipt.require_current()
    try:
        replace(receipt).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Detached impact bridge was accepted")
    many = replace(group, group_id="two", count=2, mass_per_parcel_kg=group.mass_per_parcel_kg/2)
    many_population = run_parcel_population(flash, flight, (many,),
        distribution_evidence_id="authored-two-parcels", flight_options=options)
    try:
        impact_population_member(many_population, "two", impact_owner)
    except PopulationImpactError as error:
        assert error.impact_result is None and error.cause is error.__cause__
    else:
        raise AssertionError("Representative count multiplied one finite-wall impact")
    return ValidationOutcome(True, {"contact_time_s": step.contact_end_s,
        "deposited_mass_kg": step.deposited_batch.mass_kg},
        ("Authored unit parcel/contact; no simultaneous population-wall physics",))
