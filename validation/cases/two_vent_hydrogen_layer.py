"""Deferred conservation and state-domain case for the two-vent H2 layer model."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="two-vent-hydrogen-buoyant-layer-accumulation",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_layer",
        invariants=(
            "upper-layer-interface-remains-inside-room-above-source",
            "upper-layer-H2-mole-fraction-remains-bounded",
            "source-plus-lower-inlet-mass-flow-equals-upper-outlet-mass-flow",
            "H2-release-minus-upper-vent-export-closes-layer-inventory",
            "interface-does-not-cross-source-and-vent-flow-regime-is-admitted",
            "fixed-ambient-temperature-and-still-air-limits-remain-explicit",
        ),
    ),)


def validate_layer(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.buoyant_layer import (
        TwoVentHydrogenLayerConfig,
        run_two_vent_hydrogen_layer,
    )

    config = TwoVentHydrogenLayerConfig(
        compartment_height_m=3.0,
        floor_area_m2=36.0,
        source_height_m=.2,
        lower_vent_area_m2=1.0,
        upper_vent_area_m2=1.0,
        lower_discharge_coefficient=.65,
        upper_discharge_coefficient=.65,
        ambient_pressure_pa=101325.0,
        ambient_temperature_k=293.15,
        initial_upper_layer_volume_m3=1.0,
        initial_upper_h2_mole_fraction=.1,
    )
    trace = run_two_vent_hydrogen_layer(
        config, hydrogen_mass_flow_kg_s=1.e-5,
        duration_s=600.0, maximum_step_s=.5,
    )
    assert trace.time_s[0] == 0.0 and trace.time_s[-1] == 600.0
    assert all(.2 < h < config.compartment_height_m for h in trace.interface_height_m)
    assert all(0.0 < x < 1.0 for x in trace.upper_h2_mole_fraction)
    assert all(p >= 0.0 for p in trace.compartment_overpressure_pa)
    assert all(q >= 0.0 for q in trace.lower_inflow_m3_s + trace.upper_outflow_m3_s)
    assert max(abs(r) for r in trace.hydrogen_mass_residual_kg) < 1.e-9
    assert max(abs(r) for r in trace.vent_mass_continuity_residual_kg_s) < 1.e-9
    return ValidationOutcome(True, {
        "initial_interface_height_m": trace.interface_height_m[0],
        "final_interface_height_m": trace.interface_height_m[-1],
        "final_upper_h2_mole_fraction": trace.upper_h2_mole_fraction[-1],
        "maximum_compartment_overpressure_pa": max(trace.compartment_overpressure_pa),
        "integrated_h2_release_kg": trace.cumulative_hydrogen_in_kg[-1],
        "integrated_upper_vent_h2_kg": trace.cumulative_hydrogen_out_kg[-1],
        "maximum_h2_mass_residual_kg": max(abs(r) for r in trace.hydrogen_mass_residual_kg),
        "maximum_vent_mass_residual_kg_s": max(abs(r) for r in trace.vent_mass_continuity_residual_kg_s),
    }, (
        "Authored reduced-order two-layer case only; no experimental or CFD qualification is claimed.",
        "The result assumes a vertical buoyant source in still air, fixed ambient temperature and two one-way vents.",
    ))
