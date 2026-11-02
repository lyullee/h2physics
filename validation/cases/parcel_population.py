"""Deferred weighted-parcel conservation and ownership contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="parcel-population-flash-mass-ledger", profile="droplet-transport",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("weighted liquid inventory equals post-flash liquid",
                    "common clock/frame and exact phase endpoints",
                    "typed representative traces and weighted mass closure",
                    "post-return owner mutation and detached-result rejection")),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
        flash_initial_liquid_release,
    )
    from h2physics.adapters.parcel_population import ParcelPopulationGroup, run_parcel_population
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties()
    flash = flash_initial_liquid_release(
        properties, properties.saturated(.8e6, 0.), downstream_pressure_pa=101325.,
        total_release_mass_kg=1e-6, phase_equilibrium_evidence_id="authored-equilibrium-reference")
    boundary = ParcelBoundary("population-clock", "z-up", "authored-fixed-carrier",
        .01, 1e-5, (0., 0., 0.), (0., 0., 0.), 1e5, 1., .002, .01)
    owner = SaturatedParcelFlight(properties, 101325., boundary,
        lambda state: BoilingHeat(0., "authored-adiabatic-reference"),
        force_approximation_evidence_id="authored-zero-relative-speed")
    group = ParcelPopulationGroup("identical-two", 2, flash.liquid_mass_kg/2,
        (0., 0., 1.), (0., 0., 0.), "authored-identical-parcels")
    result = run_parcel_population(flash, owner, (group,),
        distribution_evidence_id="authored-population", flight_options=dict(
            start_s=5., end_s=5.1, residual_mass_floor_kg=1e-12,
            maximum_step_s=.01, relative_tolerance=1e-9, absolute_tolerances=(1e-12,)*17))
    assert abs(result.mass_residual_kg) < 1e-15
    assert result.clock_id == boundary.clock_id and result.frame_id == boundary.frame_id
    assert result.evaporated_mass_kg == 0. and result.incident_liquid_mass_kg == 0.
    trace = result.groups_and_traces[0][1]
    original_heat = trace.heat_into_liquid_j
    object.__setattr__(trace, "heat_into_liquid_j", original_heat+1.)
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed retained flight heat ledger remained admitted")
    finally:
        object.__setattr__(trace, "heat_into_liquid_j", original_heat)
    try:
        replace(result).require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Detached population receipt was admitted")
    owner.pressure_pa = 2e5
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed flight owner retained an accepted population ledger")
    return ValidationOutcome(True, {"common_start_s": 5., "groups": 1},
        ("Authored identical isolated parcels; no size distribution or breakup qualification",))
