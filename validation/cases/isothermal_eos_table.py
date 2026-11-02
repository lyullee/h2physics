"""Held-out CoolProp comparison for the bounded isothermal-EOS lookup table."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="isothermal-eos-table-interpolation-accuracy",
        profile="isothermal-eos",
        entrypoint=__name__ + ":validate_table",
        parameters={
            "fluid": "Hydrogen",
            "density_min_kg_m3": 0.05,
            "density_max_kg_m3": 20.0,
            "temperature_min_k": 260.0,
            "temperature_max_k": 360.0,
            "density_nodes": 41,
            "temperature_nodes": 11,
            "interpolation": "log_linear",
            "validation_point_count": 512,
            "seed": 20261031,
            "maximum_relative_error": 0.01,
        },
        invariants=(
            "the table retains the direct CoolProp HEOS identity, explicit rho-T axes, interpolation mode and grid digest",
            "sampled pressure is strictly increasing in density and inverse density_pt rejects out-of-table pressure",
            "held-out log-uniform density and uniform-temperature states compare pressure, density and isothermal sound speed directly against HEOS",
            "error budget is explicit and measured speedup is recorded separately from accuracy",
            "the table is not considered qualified until every held-out relative error meets the caller budget",
            "this property-table comparison does not independently validate the pressure-wave or facility model",
        ),
    ),)


def validate_table(*, work_directory, fluid, density_min_kg_m3,
                   density_max_kg_m3, temperature_min_k, temperature_max_k,
                   density_nodes, temperature_nodes, interpolation,
                   validation_point_count, seed, maximum_relative_error):
    del work_directory
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS
    from h2physics.thermo.isothermal_eos_table import (
        IsothermalEOSTable,
        qualify_isothermal_eos_table,
    )

    if type(density_nodes) is not int or density_nodes < 2:
        raise ValueError("density_nodes must be an integer of at least two")
    if type(temperature_nodes) is not int or temperature_nodes < 2:
        raise ValueError("temperature_nodes must be an integer of at least two")
    source = CoolPropIsothermalEOS(fluid)
    density_axis = np.geomspace(density_min_kg_m3, density_max_kg_m3, density_nodes)
    temperature_axis = np.linspace(temperature_min_k, temperature_max_k,
                                  temperature_nodes)
    table = IsothermalEOSTable.from_eos(
        source, density_axis_kg_m3=density_axis,
        temperature_axis_k=temperature_axis, interpolation=interpolation,
    )
    receipt = qualify_isothermal_eos_table(
        table, source, validation_point_count=validation_point_count,
        seed=seed, maximum_relative_error=maximum_relative_error,
    )
    if not receipt.error_gate_passed:
        raise AssertionError("Held-out isothermal-EOS table interpolation exceeds the declared error budget")
    for temperature in (temperature_axis[0], temperature_axis[-1]):
        for density in (density_axis[0], density_axis[-1]):
            pressure = table.pressure_rho_t(float(density), float(temperature))
            recovered = table.density_pt(pressure, float(temperature))
            if not np.isclose(recovered, density, rtol=maximum_relative_error,
                              atol=0.0):
                raise AssertionError("Tabulated p-T density inversion failed at an inclusive envelope edge")
    try:
        table.density_pt(float(table.pressure_pa[-1, -1] * 1.001),
                         float(temperature_axis[-1]))
    except ValueError:
        pass
    else:
        raise AssertionError("Isothermal-EOS lookup silently extrapolated beyond its pressure envelope")
    return ValidationOutcome(True, {
        "source_eos_identity": receipt.source_eos_identity,
        "table_identity": receipt.table_identity,
        "table_sha256": receipt.table_sha256,
        "table_shape_temperature_density": table.shape,
        "interpolation": receipt.interpolation,
        "validation_point_count": receipt.validation_point_count,
        "seed": receipt.seed,
        "maximum_relative_pressure_error": receipt.maximum_relative_pressure_error,
        "maximum_relative_density_error": receipt.maximum_relative_density_error,
        "maximum_relative_sound_speed_error": receipt.maximum_relative_sound_speed_error,
        "maximum_relative_error_allowed": receipt.maximum_relative_error_allowed,
        "error_gate_passed": receipt.error_gate_passed,
        "measured_speedup": receipt.measured_speedup,
        "reference_seconds_per_query": receipt.reference_seconds_per_query,
        "table_seconds_per_query": receipt.table_seconds_per_query,
        "out_of_envelope_rejected": True,
    }, (
        "A passing receipt only compares this table with the selected direct CoolProp HEOS release over the declared rho-T grid.",
        "It does not establish independent EOS accuracy or qualify a pipeline, flow solver, or hydrogen facility.",
        "Timing is workload- and machine-dependent; the measured ratio is diagnostic, not a performance guarantee.",
    ))
