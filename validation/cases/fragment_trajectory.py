"""Deferred synthetic contracts for caller-defined rupture fragments."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="conditional-fragment-flight-impact",
        profile="fragment-trajectory",
        entrypoint=__name__ + ":validate_flight",
        invariants=(
            "caller-specified rigid fragment follows gravity and quadratic drag in an explicit wind field",
            "descending ground-plane crossing is localized as the impact state",
            "integrated drag impulse closes the momentum change",
            "integrated aerodynamic work closes the mechanical-energy change",
            "crosswind changes the trajectory relative to calm air",
            "no fragmentation, launch-velocity, injury or consequence probability is inferred",
        ),
    ), ValidationCase(
        identifier="fragment-flight-hydrostatic-density-profile",
        profile="fragment-trajectory",
        entrypoint=__name__ + ":validate_hydrostatic_density_profile",
        invariants=(
            "one bounded constant-lapse hydrostatic ideal-gas layer returns pressure and density from declared base conditions",
            "isothermal zero-lapse limit follows the exponential barometric relation",
            "altitude and positive-temperature domains are enforced without extrapolation",
            "the caller-owned profile plugs into the fragment-flight density callback and retains momentum/energy audits",
            "the profile is not a standard atmosphere forecast or field-specific weather record",
        ),
    ),)


def validate_flight(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment, FragmentFlightSettings, FragmentLaunch,
        integrate_fragment_flight,
    )

    def density(_height_m):
        return 1.2

    def still_air(_position_m, _time_s):
        return np.zeros(3)

    def crosswind(_position_m, _time_s):
        return np.array([0., 2., 0.])

    launch = FragmentLaunch(
        fragment_id="synthetic-rigid-fragment", mass_kg=.7,
        reference_area_m2=.025, drag_coefficient=.8,
        position_m=np.array([0., 0., 12.]),
        velocity_m_s=np.array([15., 3., 15.]), ground_z_m=0.,
        frame_id="synthetic-local-ENU",
        evidence_id="authored-launch-state-for-software-contract",
    )
    settings = FragmentFlightSettings(
        clock_id="synthetic-fragment-flight-clock",
        time_s=np.linspace(0., 8., 81), relative_tolerance=1e-9,
        absolute_tolerance=1e-11, maximum_step_s=.02,
        momentum_tolerance_kg_m_s=1e-6,
        mechanical_energy_tolerance_j=1e-5,
    )
    gravity = np.array([0., 0., -9.80665])
    calm = integrate_fragment_flight(
        launch,
        FragmentFlightEnvironment(density, still_air, gravity, launch.frame_id,
            "synthetic-uniform-air", "synthetic-constant-density", "synthetic-calm-wind"),
        settings,
    )
    wind = integrate_fragment_flight(
        launch,
        FragmentFlightEnvironment(density, crosswind, gravity, launch.frame_id,
            "synthetic-uniform-air-crosswind", "synthetic-constant-density", "synthetic-y-crosswind"),
        settings,
    )
    calm.require_current()
    wind.require_current()
    assert calm.impact_time_s is not None and wind.impact_time_s is not None
    assert abs(calm.impact_position_m[2] - launch.ground_z_m) < 1e-8
    assert abs(wind.impact_position_m[2] - launch.ground_z_m) < 1e-8
    assert calm.impact_velocity_m_s[2] < 0. and wind.impact_velocity_m_s[2] < 0.
    assert calm.drag_work_j < 0. and wind.drag_work_j < 0.
    assert abs(calm.mechanical_energy_residual_j) <= settings.mechanical_energy_tolerance_j
    assert np.max(np.abs(calm.momentum_residual_kg_m_s)) <= settings.momentum_tolerance_kg_m_s
    assert abs(wind.impact_position_m[1] - calm.impact_position_m[1]) > 1e-4
    return ValidationOutcome(True, {
        "calm_impact_time_s": calm.impact_time_s,
        "calm_impact_position_m": calm.impact_position_m.tolist(),
        "crosswind_impact_position_m": wind.impact_position_m.tolist(),
        "calm_drag_work_j": calm.drag_work_j,
        "calm_momentum_residual_kg_m_s": calm.momentum_residual_kg_m_s.tolist(),
        "calm_mechanical_energy_residual_j": calm.mechanical_energy_residual_j,
    }, (
        "Synthetic launch, rigid-body drag and uniform ambient callbacks only.",
        "No vessel-fragment generation, field-specific atmosphere or human/facility damage model.",
    ))


def validate_hydrostatic_density_profile(*, work_directory, **parameters):
    """Deferred profile equation and fragment-flight callback integration."""
    del work_directory, parameters
    import math
    import numpy as np

    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment, FragmentFlightSettings, FragmentLaunch,
        HydrostaticIdealGasDensityProfile, integrate_fragment_flight,
    )

    gravity = 9.80665
    gas_constant = 8.31446261815324 / 0.028965
    profile = HydrostaticIdealGasDensityProfile(
        base_altitude_m=0.0, base_pressure_pa=101325.0,
        base_temperature_k=288.15, lapse_rate_k_m=0.0065,
        molecular_mass_kg_mol=0.028965, gravity_m_s2=gravity,
        minimum_altitude_m=0.0, maximum_altitude_m=5000.0,
        evidence_id="synthetic-caller-atmosphere-layer",
    )
    altitude = 1500.0
    expected_temperature = 288.15 - 0.0065 * altitude
    expected_pressure = 101325.0 * (expected_temperature / 288.15) ** (
        gravity / (gas_constant * 0.0065))
    assert math.isclose(profile.temperature_at(altitude), expected_temperature, rel_tol=1e-14)
    assert math.isclose(profile.pressure_at(altitude), expected_pressure, rel_tol=1e-13)
    assert math.isclose(
        profile.density_kg_m3(altitude),
        expected_pressure / (gas_constant * expected_temperature), rel_tol=1e-13,
    )
    isothermal = HydrostaticIdealGasDensityProfile(
        base_altitude_m=0.0, base_pressure_pa=101325.0,
        base_temperature_k=288.15, lapse_rate_k_m=0.0,
        molecular_mass_kg_mol=0.028965, gravity_m_s2=gravity,
        minimum_altitude_m=0.0, maximum_altitude_m=5000.0,
        evidence_id="synthetic-isothermal-atmosphere-layer",
    )
    isothermal_pressure = 101325.0 * math.exp(-gravity * altitude / (
        gas_constant * 288.15))
    assert math.isclose(isothermal.pressure_at(altitude), isothermal_pressure, rel_tol=1e-13)
    try:
        profile.density_kg_m3(5000.1)
    except ValueError as error:
        assert "outside the declared" in str(error)
    else:
        raise AssertionError("profile extrapolated outside its altitude domain")

    launch = FragmentLaunch(
        fragment_id="synthetic-atmosphere-profile-fragment", mass_kg=0.7,
        reference_area_m2=0.025, drag_coefficient=0.8,
        position_m=np.array([0.0, 0.0, 250.0]),
        velocity_m_s=np.array([18.0, 0.0, 0.0]), ground_z_m=0.0,
        frame_id="synthetic-profile-ENU", evidence_id="synthetic-launch",
    )
    settings = FragmentFlightSettings(
        clock_id="synthetic-profile-flight-clock",
        time_s=np.linspace(0.0, 30.0, 61), maximum_step_s=0.05,
        momentum_tolerance_kg_m_s=1e-5,
        mechanical_energy_tolerance_j=1e-4,
    )
    environment = FragmentFlightEnvironment(
        density_kg_m3=profile,
        wind_velocity_m_s=lambda position, time: np.zeros(3),
        gravity_m_s2=np.array([0.0, 0.0, -gravity]),
        frame_id=launch.frame_id, evidence_id="synthetic-hydrostatic-environment",
        density_evidence_id=profile.evidence_id, wind_evidence_id="synthetic-still-air",
    )
    flight = integrate_fragment_flight(launch, environment, settings)
    flight.require_current()
    assert flight.impact_time_s is not None
    assert 0.0 < flight.impact_time_s <= settings.time_s[-1]
    return ValidationOutcome(
        True,
        {
            "density_at_base_kg_m3": profile.density_kg_m3(0.0),
            "density_at_1500m_kg_m3": profile.density_kg_m3(altitude),
            "temperature_at_1500m_k": profile.temperature_at(altitude),
            "fragment_impact_time_s": flight.impact_time_s,
            "fragment_impact_range_m": float(np.linalg.norm(flight.impact_position_m[:2])),
            "maximum_momentum_residual_kg_m_s": float(np.max(
                np.abs(flight.momentum_residual_kg_m_s))),
            "mechanical_energy_residual_j": flight.mechanical_energy_residual_j,
        },
        (
            "Synthetic hydrostatic layer and caller parameters only; not an atmosphere data product or forecast.",
            "Rigid-fragment trajectory remains conditional on the supplied launch state and drag law.",
        ),
    )
