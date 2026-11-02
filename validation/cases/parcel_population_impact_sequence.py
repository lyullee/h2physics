"""Deferred sequence of distinct unit-count parcel impacts through one finite patch."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="parcel-population-finite-impact-sequence",
        profile="droplet-impact",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "all accepted unit-count ground events are ordered by their native event times",
            "one existing finite surface owner evolves its wall state across distinct contacts",
            "population incident mass matches the summed finite-wall contact stock",
            "multi-count representative groups and equal-time contacts are rejected",
            "original flight traces and owner-issued impact steps remain linked",
            "the composition claims no simultaneous contact or wet-pool spreading physics",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
        flash_initial_liquid_release,
    )
    from h2physics.adapters.parcel_population import (
        ParcelPopulationGroup,
        run_parcel_population,
    )
    from h2physics.adapters.parcel_population_impact_sequence import (
        PopulationImpactSequenceError,
        impact_population_sequence,
    )
    from examples.droplet_impact import build_model

    del work_directory, parameters
    impact_owner = build_model()
    properties = impact_owner.properties
    flash = flash_initial_liquid_release(
        properties,
        properties.saturated(.8e6, 0.),
        downstream_pressure_pa=101325.,
        total_release_mass_kg=1e-6,
        phase_equilibrium_evidence_id="authored-sequence-flash",
    )
    location = impact_owner.patch.location
    boundary = ParcelBoundary(
        location.clock_id, location.coordinate_frame_id,
        "authored-low-speed-vacuum-flight-boundary",
        .01, 1e-5, (0., 0., 0.), (0., 0., 0.),
        1e5, 1., .002, .01,
    )
    flight = SaturatedParcelFlight(
        properties, 101325., boundary,
        lambda state: BoilingHeat(0., "authored-zero-flight-heat"),
        force_approximation_evidence_id="authored-zero-relative-force-limit",
    )
    parcel_mass = flash.launch_liquid_mass_kg/2
    groups = (
        # Short, distinct fall paths make both terminal ground events explicit
        # while keeping the native low-Re/low-We parcel gates comfortably open.
        ParcelPopulationGroup("upper", 1, parcel_mass, (0., 0., .20),
                             (0., 0., -.5), "authored-two-position-groups"),
        ParcelPopulationGroup("lower", 1, parcel_mass, (0., 0., .10),
                             (0., 0., -.5), "authored-two-position-groups"),
    )
    options = dict(
        start_s=100., end_s=120., residual_mass_floor_kg=1e-8,
        maximum_step_s=.02, relative_tolerance=1e-9,
        absolute_tolerances=(1e-12,)*17, ground_z_m=0.,
    )
    population = run_parcel_population(
        flash, flight, groups, distribution_evidence_id="authored-two-unit-events",
        flight_options=options,
    )
    result = impact_population_sequence(population, impact_owner)
    assert result.group_ids == ("lower", "upper")
    assert result.event_times_s[0] < result.event_times_s[1]
    assert len(result.impact_result.steps) == 2
    assert all(step.context.incident_trace is trace for step, (_, trace) in zip(
        result.impact_result.steps, sorted(
            population.groups_and_traces, key=lambda pair: pair[1].states[-1].time_s),
        strict=True,
    ))
    assert result.impact_result.total_incident_mass_kg == population.incident_liquid_mass_kg
    assert result.require_current() is result

    grouped = ParcelPopulationGroup(
        "representative-multiplicity", 2, flash.launch_liquid_mass_kg/2,
        (0., 0., 1.0), (0., 0., -.11), "authored-grouped-launch",
    )
    grouped_population = run_parcel_population(
        flash, flight, (grouped,), distribution_evidence_id="authored-grouped-launch",
        flight_options=options,
    )
    try:
        impact_population_sequence(grouped_population, impact_owner)
    except PopulationImpactSequenceError as error:
        assert error.impact_result is None
        assert isinstance(error.cause, ValueError)
        multiplicity_rejected = True
    else:
        raise AssertionError("Representative parcel count was multiplied into repeated wall contacts")

    return ValidationOutcome(True, {
        "unit_contacts": len(result.impact_result.steps),
        "ordered_group_ids": result.group_ids,
        "combined_incident_mass_kg": result.impact_result.total_incident_mass_kg,
        "combined_mass_residual_kg": result.impact_result.mass_residual_kg,
        "combined_energy_residual_j": result.impact_result.total_energy_residual_j,
        "multi_count_group_rejected": multiplicity_rejected,
    }, (
        "Synthetic low-speed unit-parcel sequence only; no population-distribution, simultaneous-impact, deposition, wet-pool, or measured-impact qualification is implied.",
    ))
