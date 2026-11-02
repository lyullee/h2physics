"""Deferred Hangang contract for EOS-backed isothermal gas linepack."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-pipeline-real-gas-linepack-eos",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_real_gas_linepack",
        parameters={
            "volume_m3": 2.0,
            "temperature_k": 293.15,
            "initial_pressure_pa": 7.0e6,
            "minimum_pressure_pa": 1.0e6,
            "maximum_pressure_pa": 1.0e7,
        },
        invariants=(
            "initial-pressure-reconstructed-through-the-declared-isothermal-eos",
            "accepted-fixed-volume-inventory-uses-no-ideal-gas-fallback",
            "prescribed-inlet-and-outlet-masses-close-exactly",
            "pressure-domain-and-inventory-floor-reject-without-flow-clipping",
            "an-eos-identity-change-invalidates-continuation",
            "lumped-isothermal-eos-result-is-not-a-spatial-pipeline-solver",
        ),
    ),)


def validate_real_gas_linepack(*, work_directory, **parameters):
    """Check EOS inversion, mass closure, bounds, and EOS ownership."""
    del work_directory
    from math import isclose

    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

    eos = CoolPropIsothermalEOS("Hydrogen")
    state = RealGasLinepackState.from_pressure(
        volume_m3=parameters["volume_m3"],
        temperature_k=parameters["temperature_k"],
        pressure_pa=parameters["initial_pressure_pa"],
        eos=eos,
        minimum_pressure_pa=parameters["minimum_pressure_pa"],
        maximum_pressure_pa=parameters["maximum_pressure_pa"],
    )
    assert isclose(state.pressure_pa, parameters["initial_pressure_pa"],
                   rel_tol=1e-8, abs_tol=1e-2)
    charged, charge_ledger = state.advance(
        duration_s=20.0, inlet_mass_flow_kg_s=0.05,
        outlet_mass_flow_kg_s=0.01, minimum_mass_kg=0.01,
    )
    assert charged.mass_kg > state.mass_kg
    assert charged.pressure_pa > state.pressure_pa
    assert abs(charge_ledger.mass_residual_kg) <= 1e-12
    try:
        state.advance(duration_s=20.0, inlet_mass_flow_kg_s=0.0,
                      outlet_mass_flow_kg_s=state.mass_kg/20.0,
                      minimum_mass_kg=0.01)
    except ValueError as error:
        assert "mass floor" in str(error)
    else:
        raise AssertionError("An inventory-floor crossing was accepted")
    try:
        state.advance(duration_s=200.0, inlet_mass_flow_kg_s=0.1,
                      outlet_mass_flow_kg_s=0.0, minimum_mass_kg=0.01)
    except ValueError:
        pressure_bound_rejected = True
    else:
        raise AssertionError("A state outside the declared pressure bound was accepted")
    eos.fluid = "Methane"
    try:
        state.advance(duration_s=1.0, inlet_mass_flow_kg_s=0.0,
                      outlet_mass_flow_kg_s=0.0)
    except ValueError as error:
        assert "EOS identity changed" in str(error)
        eos_mutation_rejected = True
    else:
        raise AssertionError("An EOS identity mutation was accepted")
    return ValidationOutcome(True, {
        "eos_identity": state.eos_identity,
        "initial_pressure_pa": state.pressure_pa,
        "charged_pressure_pa": charged.pressure_pa,
        "mass_residual_kg": charge_ledger.mass_residual_kg,
        "pressure_bound_rejected": pressure_bound_rejected,
        "eos_mutation_rejected": eos_mutation_rejected,
    }, (
        "CoolProp HEOS single-phase isothermal EOS contract only",
        "The interval is well mixed and isothermal; wall heat and flow hydraulics are absent",
        "No measured linepack transient or full pipeline qualification is established",
    ))
