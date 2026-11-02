"""Deferred composition-closure case for an upper-layer oxygen projection."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="two-vent-layer-dry-air-oxygen-composition-projection",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_projection",
        invariants=(
            "oxygen-mole-fraction-follows-retained-binary-layer-composition",
            "exact-source-clock-and-trace-identity-are-preserved",
            "non-dry-air-carrier-basis-is-rejected",
            "projection-is-not-a-homogeneous-room-or-human-response-result",
        ),
    ),)


def validate_projection(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.layer_oxygen_projection import project_layer_oxygen
    from h2physics.buoyant_layer import (
        TwoVentHydrogenLayerConfig,
        run_two_vent_hydrogen_layer,
    )

    config = TwoVentHydrogenLayerConfig(
        compartment_height_m=3.0,
        floor_area_m2=36.0,
        source_height_m=0.2,
        lower_vent_area_m2=1.0,
        upper_vent_area_m2=1.0,
        lower_discharge_coefficient=0.65,
        upper_discharge_coefficient=0.65,
        ambient_pressure_pa=101325.0,
        ambient_temperature_k=293.15,
        initial_upper_layer_volume_m3=1.0,
        initial_upper_h2_mole_fraction=0.1,
    )
    trace = run_two_vent_hydrogen_layer(
        config,
        hydrogen_mass_flow_kg_s=1e-5,
        duration_s=2.0,
        maximum_step_s=0.5,
    )
    projection = project_layer_oxygen(
        trace,
        carrier_basis="fixed_dry_air",
        carrier_oxygen_mole_fraction=trace.dry_air_mole_fractions[1],
    )
    assert projection.layer_trace is trace
    assert projection.time_s is trace.time_s
    assert len(projection.upper_oxygen_mole_fraction) == len(trace.time_s)
    assert all(
        abs(o2 - (1.0 - h2) * trace.dry_air_mole_fractions[1]) < 1e-15
        for o2, h2 in zip(
            projection.upper_oxygen_mole_fraction,
            trace.upper_h2_mole_fraction,
            strict=True,
        )
    )
    rejected = False
    try:
        project_layer_oxygen(
            trace,
            carrier_basis="unknown_mixture",
            carrier_oxygen_mole_fraction=0.2095,
        )
    except ValueError:
        rejected = True
    assert rejected
    return ValidationOutcome(True, {
        "sample_count": len(projection.time_s),
        "initial_upper_o2_mole_fraction": projection.upper_oxygen_mole_fraction[0],
        "final_upper_o2_mole_fraction": projection.upper_oxygen_mole_fraction[-1],
        "carrier_basis": projection.carrier_basis,
    }, (
        "Composition projection only; no homogeneous-room oxygen model or human-response law is evaluated.",
        "Assumes upper-layer gas contains H2 plus the caller-declared fixed dry-air carrier.",
    ))
