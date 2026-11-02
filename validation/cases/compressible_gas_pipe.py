"""Deferred synthetic isothermal compressible-gas pipe contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="isothermal-compressible-gas-pipe-momentum",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_momentum_balance",
            invariants=(
                "steady horizontal ideal-gas momentum includes Darcy wall friction and axial acceleration",
                "mass flow solves the Reynolds-dependent caller friction law and integrated pressure relation",
                "ideal-gas density variation produces distinct inlet/outlet velocity at constant mass flow",
                "pressure residual is independently reconstructed within caller tolerances",
                "elevation, heat, local losses, real-gas EOS, choking and transient line inventory are excluded",
            ),
        ),
    )


def validate_momentum_balance(*, work_directory, **parameters):
    """Compare the solver with a separately evaluated constant-friction relation."""
    del work_directory, parameters
    import math
    from h2physics.hydraulics import (
        DarcyGeometry, solve_isothermal_compressible_gas_flow,
    )

    geometry = DarcyGeometry(
        length_m=120.0, diameter_m=0.02, roughness_m=1e-6,
    )
    upstream, downstream, temperature = 8.0e6, 6.0e6, 300.0
    molar_mass, viscosity, friction = 0.00201588, 9.0e-6, 0.024
    result = solve_isothermal_compressible_gas_flow(
        geometry,
        upstream_pressure_pa=upstream,
        downstream_pressure_pa=downstream,
        temperature_k=temperature,
        molecular_mass_kg_mol=molar_mass,
        viscosity_pa_s=viscosity,
        friction_law=lambda reynolds, relative_roughness: friction,
        friction_law_id="synthetic constant Darcy factor",
    )
    gas_constant = 8.31446261815324 / molar_mass
    area = math.pi * geometry.diameter_m**2 / 4.0
    resistance = (friction * geometry.length_m / geometry.diameter_m
                  + 2.0 * math.log(upstream / downstream))
    expected_flow = area * math.sqrt(
        (upstream**2 - downstream**2) / (gas_constant * temperature * resistance)
    )
    assert math.isclose(result.mass_flow_kg_s, expected_flow, rel_tol=2e-12)
    assert math.isclose(
        result.reynolds_number,
        result.mass_flow_kg_s * geometry.diameter_m / (area * viscosity),
        rel_tol=2e-12,
    )
    assert result.outlet_velocity_m_s > result.inlet_velocity_m_s
    assert abs(result.pressure_residual_pa) <= max(
        1e-5, 1e-9 * (upstream - downstream))
    try:
        solve_isothermal_compressible_gas_flow(
            DarcyGeometry(120.0, 0.02, 1e-6, local_loss_coefficient=1.0),
            upstream_pressure_pa=upstream, downstream_pressure_pa=downstream,
            temperature_k=temperature, molecular_mass_kg_mol=molar_mass,
            viscosity_pa_s=viscosity,
            friction_law=lambda reynolds, relative_roughness: friction,
            friction_law_id="synthetic constant Darcy factor",
        )
    except ValueError as error:
        assert "zero local-loss" in str(error)
    else:
        raise AssertionError("the unsupported local-loss term was accepted")
    return ValidationOutcome(
        True,
        {
            "mass_flow_kg_s": result.mass_flow_kg_s,
            "reynolds_number": result.reynolds_number,
            "friction_factor": result.darcy_friction_factor,
            "inlet_velocity_m_s": result.inlet_velocity_m_s,
            "outlet_velocity_m_s": result.outlet_velocity_m_s,
            "pressure_residual_pa": result.pressure_residual_pa,
        },
        (
            "Synthetic constant-friction ideal-gas equation contract only; no experimental or hydrogen-pipe validation.",
            "Steady, horizontal, isothermal, single-phase perfect gas; choking and real-gas corrections are excluded.",
        ),
    )
