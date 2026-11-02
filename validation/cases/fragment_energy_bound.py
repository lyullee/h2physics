"""Deferred contracts for elastic-energy-limited fragment speed envelopes."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cylinder-elastic-fragment-speed-ceiling",
        profile="fragment-trajectory",
        entrypoint=__name__ + ":validate_energy_bound",
        invariants=(
            "closed-end Lamé field energy integrates to its exact annular expression",
            "open-end support changes the longitudinal elastic-energy contribution",
            "assigned fragment energy cannot exceed the specified fraction of strain energy",
            "speed closes against fragment mass and allocated kinetic energy",
            "external baseline pressure, unstable elastic constants and invalid fractions are rejected",
            "the envelope does not infer breach, fragment generation, launch direction or structural impact",
        ),
    ), ValidationCase(
        identifier="elastic-bound-fragment-flight-handoff",
        profile="fragment-trajectory",
        entrypoint=__name__ + ":validate_elastic_bound_flight",
        invariants=(
            "existing Lamé speed ceiling admits only a caller launch within assigned energy",
            "exact event time and clock are the first flight sample",
            "environment, fragment and cylinder use the explicitly declared frame",
            "the receipt retains both pressure-energy source and accepted flight result",
            "no failure, fragmentation or launch kinematics are inferred",
        ),
    ),)


def validate_energy_bound(*, work_directory, **parameters):
    from math import isclose

    import numpy as np

    from h2physics.core import Origin
    from h2physics.fragment_energy_bound import bound_fragment_speed_from_elastic_energy
    from h2physics.materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad

    del work_directory, parameters
    geometry = CylinderGeometry(.08, .10, "closed", "synthetic-vessel-section")
    load = CylinderPressureLoad(8.0e6, 0.0, "synthetic-differential-load", Origin.SYNTHETIC)
    result = bound_fragment_speed_from_elastic_energy(
        geometry, load, cylinder_length_m=1.5, youngs_modulus_pa=2.0e11,
        poisson_ratio=.3, fragment_mass_kg=2.0, fragment_energy_fraction=.2,
        fragment_id="synthetic-shell-piece", material_evidence_id="synthetic-elastic-constants",
    )
    ri, ro = geometry.inner_radius_m, geometry.outer_radius_m
    a = load.internal_pressure_pa * ri**2 / (ro**2-ri**2)
    b = load.internal_pressure_pa * ri**2 * ro**2 / (ro**2-ri**2)
    p, e, nu, length = load.internal_pressure_pa, 2.0e11, .3, 1.5
    del p
    closed_expected = np.pi*length/e * (
        (2*(1-nu)*a*a+a*a-4*nu*a*a)*(ro**2-ri**2)/2
        +2*(1+nu)*b*b*(1/ri**2-1/ro**2)/2
    )
    assert isclose(result.elastic_strain_energy_j, closed_expected, rel_tol=2e-14)
    assert isclose(.5*result.fragment_mass_kg*result.maximum_speed_m_s**2,
                   result.available_fragment_energy_j, rel_tol=2e-14)
    open_geometry = CylinderGeometry(.08, .10, "open", "synthetic-open-section")
    open_result = bound_fragment_speed_from_elastic_energy(
        open_geometry, load, cylinder_length_m=length, youngs_modulus_pa=e,
        poisson_ratio=nu, fragment_mass_kg=2.0, fragment_energy_fraction=.2,
        fragment_id="synthetic-shell-piece", material_evidence_id="synthetic-elastic-constants",
    )
    assert result.elastic_strain_energy_j != open_result.elastic_strain_energy_j
    for invalid in (
        lambda: bound_fragment_speed_from_elastic_energy(
            geometry, CylinderPressureLoad(8e6, 1e5, "external", Origin.SYNTHETIC),
            cylinder_length_m=length, youngs_modulus_pa=e, poisson_ratio=nu,
            fragment_mass_kg=2., fragment_energy_fraction=.2, fragment_id="piece",
            material_evidence_id="fixture",
        ),
        lambda: bound_fragment_speed_from_elastic_energy(
            geometry, load, cylinder_length_m=length, youngs_modulus_pa=e,
            poisson_ratio=.5, fragment_mass_kg=2., fragment_energy_fraction=.2,
            fragment_id="piece", material_evidence_id="fixture",
        ),
    ):
        try:
            invalid()
        except ValueError:
            pass
        else:
            raise AssertionError("An invalid elastic-bound input was admitted")
    return ValidationOutcome(True, {
        "closed_end_elastic_energy_j": result.elastic_strain_energy_j,
        "open_end_elastic_energy_j": open_result.elastic_strain_energy_j,
        "fragment_energy_j": result.available_fragment_energy_j,
        "maximum_speed_m_s": result.maximum_speed_m_s,
    }, ("Synthetic linear-elastic envelope only; it does not predict actual vessel failure or fragment launch",))



def validate_elastic_bound_flight(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.adapters.elastic_fragment_flight import run_elastic_bound_fragment_flight
    from h2physics.fragment_energy_bound import bound_fragment_speed_from_elastic_energy
    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment, FragmentFlightSettings, FragmentLaunch,
    )
    from h2physics.materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad
    from h2physics.core import Origin

    geometry = CylinderGeometry(.08, .10, "closed", "authored-elastic-bound-cylinder")
    pressure = CylinderPressureLoad(8.0e6, 0.0, "authored-differential-pressure", Origin.SYNTHETIC)
    bound = bound_fragment_speed_from_elastic_energy(
        geometry, pressure, cylinder_length_m=1.5, youngs_modulus_pa=2.0e11,
        poisson_ratio=.3, fragment_mass_kg=2.0, fragment_energy_fraction=.2,
        fragment_id="authored-single-rigid-piece", material_evidence_id="synthetic-elastic-constants",
    )
    velocity = np.array([.25*bound.maximum_speed_m_s, 0., .25*bound.maximum_speed_m_s])
    launch = FragmentLaunch(
        bound.fragment_id, bound.fragment_mass_kg, .025, .8,
        np.array([0., 0., 2.]), velocity, 0., "authored-local-ENU",
        "caller-authored-fragment-state-within-energy-ceiling",
    )
    environment = FragmentFlightEnvironment(
        lambda _height: 1.2,
        lambda _position, _time: np.zeros(3), np.array([0., 0., -9.80665]),
        launch.frame_id, "authored-constant-air-environment",
        "authored-density", "authored-calm-wind",
    )
    settings = FragmentFlightSettings(
        "authored-pressure-release-clock", np.linspace(2., 8., 301),
        maximum_step_s=.02, momentum_tolerance_kg_m_s=1e-4,
        mechanical_energy_tolerance_j=1e-3,
    )
    result = run_elastic_bound_fragment_flight(
        geometry, pressure, cylinder_length_m=1.5,
        youngs_modulus_pa=2.0e11, poisson_ratio=.3,
        fragment_energy_fraction=.2,
        material_evidence_id="synthetic-elastic-constants",
        launch=launch, environment=environment, settings=settings,
        event_time_s=2., event_evidence_id="authored-conditional-pressure-event",
        launch_mapping_evidence_id="authored-caller-owned-vessel-to-fragment-map",
    )
    result.require_current()
    assert result.flight.launch is launch
    assert result.flight.time_s[0] == result.event_time_s
    assert .5*launch.mass_kg*float(launch.velocity_m_s @ launch.velocity_m_s) <= result.energy_bound.available_fragment_energy_j
    return ValidationOutcome(True, {
        "ceiling_m_s": result.energy_bound.maximum_speed_m_s,
        "launch_speed_m_s": float(np.linalg.norm(launch.velocity_m_s)),
        "impact_time_s": result.flight.impact_time_s,
    }, ("Synthetic linear-elastic pressure energy and caller launch only; no rupture or fragmentation prediction",))
