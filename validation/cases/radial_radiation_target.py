"""Deferred source-interval to radial-wall coupling contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="radial-radiation-target-source-ledger", profile="thermal-utilities",
        entrypoint=__name__+":validate_target", parameters={}, invariants=(
            "source discontinuities create exact separate radial solves",
            "absorbed incident energy closes outer-face and finite-wall ledgers",
            "source clock and original native results retained",
            "changed source arrays invalidate downstream target receipt",
        ),
    ),)


def validate_target(*, work_directory, **parameters):
    import numpy as np

    from h2physics.adapters.radial_radiation_target import run_radial_radiation_target
    from h2physics.adapters.thermal_target import IncidentHeatHistory
    from h2physics.core import Origin
    from h2physics.materials.radial_heat import RadialSolidMaterial, RadialThermalBoundary

    history = IncidentHeatHistory(
        np.array([10., 11., 13.]), np.array([100., 200.]),
        "authored-clock", "fixed-cylinder-frame", "authored-irradiation",
        "outer-cylinder", "authored-uniform-flux", Origin.SYNTHETIC, object(),
    )
    result = run_radial_radiation_target(
        history, inner_radius_m=.09, outer_radius_m=.1, length_m=1.,
        material=RadialSolidMaterial(7800., lambda t: 500., lambda t: 15.,
                                    "authored-solid", "authored-constant-properties"),
        initial_temperature_k=300.,
        inner_boundary=RadialThermalBoundary("adiabatic", 0., "authored-insulated-inner"),
        absorptivity=.5, geometry_evidence_id="authored-cylinder-dimensions",
        evidence_id="authored-radial-conduction", uniform_circumference_evidence_id="authored-uniformity",
        cells=6, maximum_step_s=.05, energy_tolerance_j=1e-3,
    )
    assert result.require_current() is result
    assert len(result.segments) == 2
    assert result.segments[0].time_s[-1] == result.segments[1].time_s[0] == 11.
    assert np.array_equal(result.segments[0].temperature_k[-1],
                          result.segments[1].temperature_k[0])
    assert all(segment.clock_id == history.clock_id for segment in result.segments)
    stored = sum(segment.stored_energy_j[-1]-segment.stored_energy_j[0]
                 for segment in result.segments)
    assert abs(stored-result.absorbed_incident_j) < 1e-3
    history.incident_flux_w_m2.setflags(write=True)
    history.incident_flux_w_m2[0] += 1.
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed incident source retained target admission")
    return ValidationOutcome(True, {"absorbed_incident_j": result.absorbed_incident_j,
                                    "outer_heat_residual_j": result.outer_heat_residual_j},
                             ("Uniform outer prescribed absorbed flux only",
                              "No reradiation, outer convection, axial gradient, damage or injury"))
