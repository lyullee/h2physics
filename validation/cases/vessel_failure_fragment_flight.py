"""Deferred source-bound HELPR initiation to conditional fragment-flight case."""

import sys
from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="vessel-failure-fragment-flight-handoff",
        profile="fracture-fatigue",
        entrypoint=__name__ + ":validate_fragment_flight_handoff",
        parameters={},
        invariants=(
            "native HELPR initiation time/pressure and clock bind to exact first flight sample",
            "HELPR shell dimensions require explicit cylinder support and length mapping",
            "caller fragment launch remains below the existing elastic energy ceiling",
            "no breach, fragment generation or launch velocity is inferred",
        ),
    ),)


def validate_fragment_flight_handoff(*, work_directory, native_packages=None, **parameters):
    del work_directory, parameters
    import numpy as np

    if native_packages is not None:
        if not isinstance(native_packages, str) or not native_packages.strip():
            raise TypeError("native_packages must identify the staged, pinned HELPR source")
        path = str(__import__("pathlib").Path(native_packages).resolve())
        if path not in sys.path:
            sys.path.insert(0, path)

    from examples.vessel_failure import authored_case
    from h2physics.adapters.vessel_failure import HelprVesselFailure
    from h2physics.adapters.vessel_failure_fragment_flight import run_vessel_failure_fragment_flight
    from h2physics.core import Origin
    from h2physics.fragment_energy_bound import bound_fragment_speed_from_elastic_energy
    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment, FragmentFlightSettings, FragmentLaunch,
    )
    from h2physics.materials.elastic_cylinder import CylinderGeometry, CylinderPressureLoad

    flaw, law, history = authored_case(thermal_weakening=True)
    owner = HelprVesselFailure(
        flaw, law, criterion="separate_yield_and_toughness",
        criterion_evidence_id="authored-verification-criterion-not-standard-conformity",
    )
    prediction = owner.predict(history, maximum_reconstruction_step_s=1.0)
    if prediction.initiation is None:
        raise AssertionError("Authored HELPR contract requires an initiation event")
    event = prediction.initiation
    context, geometry_spec = prediction.history.context, prediction.geometry
    outer = geometry_spec.outer_diameter_m/2.0
    inner = outer-geometry_spec.wall_thickness_m
    cylinder = CylinderGeometry(inner, outer, "closed",
        f"{context.vessel_id}:{geometry_spec.geometry_id}:elastic-bound-cylinder")
    pressure = CylinderPressureLoad(event.loading.pressure_difference_pa, 0.0,
        f"{context.vessel_id}:{context.clock_id}:{event.loading.time_s}:failure-pressure-difference",
        Origin(context.origin))
    bound = bound_fragment_speed_from_elastic_energy(
        cylinder, pressure, cylinder_length_m=1.0,
        youngs_modulus_pa=2.0e11, poisson_ratio=.3,
        fragment_mass_kg=2.0, fragment_energy_fraction=.1,
        fragment_id="authored-single-shell-piece",
        material_evidence_id="authored-independent-elastic-constant-assumption",
    )
    velocity = np.array([.2*bound.maximum_speed_m_s, 0., .2*bound.maximum_speed_m_s])
    launch = FragmentLaunch(
        bound.fragment_id, bound.fragment_mass_kg, .02, .8,
        np.array([0., 0., 2.]), velocity, 0., context.frame_id,
        "authored-caller-specified-fragment-state",
    )
    environment = FragmentFlightEnvironment(
        lambda _height: 1.2,
        lambda _position, _time: np.zeros(3), np.array([0., 0., -9.80665]),
        context.frame_id, "authored-constant-air-environment",
        "authored-density", "authored-calm-wind",
    )
    start = event.loading.time_s
    settings = FragmentFlightSettings(
        context.clock_id, np.linspace(start, start+8., 401),
        maximum_step_s=.02, momentum_tolerance_kg_m_s=1e-4,
        mechanical_energy_tolerance_j=1e-3,
    )
    result = run_vessel_failure_fragment_flight(
        prediction, end_condition="closed", cylinder_length_m=1.0,
        shell_to_cylinder_evidence_id="authored-HELPR-flaw-shell-to-long-cylinder-map",
        youngs_modulus_pa=2.0e11, poisson_ratio=.3,
        fragment_energy_fraction=.1,
        material_evidence_id="authored-independent-elastic-constant-assumption",
        launch=launch, environment=environment, settings=settings,
        launch_mapping_evidence_id="authored-failure-location-to-fragment-launch-map",
    )
    result.require_current()
    assert result.prediction is prediction
    assert result.flight.time_s[0] == event.loading.time_s
    assert result.flight.launch is launch
    return ValidationOutcome(True, {
        "initiation_time_s": event.loading.time_s,
        "initiation_pressure_difference_pa": event.loading.pressure_difference_pa,
        "elastic_ceiling_m_s": result.bound_flight.energy_bound.maximum_speed_m_s,
        "launch_speed_m_s": float(np.linalg.norm(launch.velocity_m_s)),
        "impact_time_s": result.flight.impact_time_s,
    }, ("HELPR initiation is not a breach or fragment launch model; launch state is caller supplied",))
