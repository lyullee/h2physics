"""Deferred caller-map composition for the existing open Brayton reference."""

import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


LIMITS = (
    "Map grids are caller-owned and are not predictions or independently qualified data.",
    "Cantera and the existing open Brayton runner own gas properties and HP equilibrium.",
    "Corrected-speed linking and flow-correction factors remain caller evidence.",
    "A shaft residual is reported at the selected point; common-speed search and closure are absent.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-brayton-compressor-turbine-map-pair",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_map_pair",
            invariants=(
                "bounded-compressor-map-interpolation",
                "compressor-map-flow-matches-inlet-air-flow",
                "turbine-map-flow-matches-air-plus-hydrogen-flow",
                "both-mapped-efficiencies-feed-existing-native-cycle",
                "component-speed-link-evidence-retained",
                "shaft-residual-recomputed-without-claiming-closure",
                "map-domain-and-flow-mismatch-rejected",
                "result-and-map-source-mutation-rejected",
            ),
        ),
    )


def validate_map_pair(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import cantera as ct

    from h2physics.combustion.open_brayton import OpenBraytonInputs
    from h2physics.combustion.turbine_map import TurbineComponentMap
    from h2physics.combustion.compressor_map import (
        CompressorComponentMap,
        MapMatchedBraytonInputs,
        MapMatchedBraytonRun,
        interpolate_compressor_map,
        run_map_matched_brayton,
    )

    compressor_map = CompressorComponentMap(
        map_id="synthetic-gas-compressor-map",
        evidence_id="synthetic-compressor-grid",
        source_uri="urn:h2physics:synthetic-compressor-grid",
        license_id="NOASSERTION",
        source_sha256="0" * 64,
        speed_unit="caller-corrected-speed",
        pressure_ratio_convention="outlet-over-inlet-total-pressure",
        corrected_mass_flow_basis="kg/s at caller-declared compressor correction reference",
        corrected_speed=(0.5, 1.0),
        compression_pressure_ratio=(6.0, 10.0),
        corrected_mass_flow_kg_s=((1.0, 1.0), (1.0, 1.0)),
        isentropic_efficiency=((0.82, 0.84), (0.86, 0.88)),
    )
    compressor_point = interpolate_compressor_map(
        compressor_map, corrected_speed=0.75, compression_pressure_ratio=8.0)
    assert math.isclose(compressor_point.corrected_mass_flow_kg_s, 1.0, abs_tol=1e-12)
    assert math.isclose(compressor_point.isentropic_efficiency, 0.85, abs_tol=1e-12)

    cycle_inputs = OpenBraytonInputs(
        mechanism_id="gri30.yaml-deferred",
        process_window_id="steady-point-map-pair",
        air_temperature_k=288.15,
        air_pressure_pa=101325.0,
        air_mole_fractions=(("O2", 0.21), ("N2", 0.79)),
        compressor_pressure_ratio=8.0,
        compressor_isentropic_efficiency=0.85,
        combustor_pressure_recovery=0.97,
        hydrogen_fuel_to_air_mass_ratio=0.02,
        hydrogen_inlet_temperature_k=298.15,
        turbine_exhaust_pressure_pa=101325.0,
        turbine_isentropic_efficiency=0.88,
        hydrogen_lhv_j_kg=120.0e6,
        air_state_evidence_id="synthetic-air-boundary",
        hydrogen_feed_evidence_id="synthetic-hydrogen-boundary",
        machine_parameter_evidence_id="synthetic-map-operating-point",
        lhv_evidence_id="synthetic-lhv-basis",
    )
    turbine_map = TurbineComponentMap(
        map_id="synthetic-gas-turbine-map",
        evidence_id="synthetic-turbine-grid",
        source_uri="urn:h2physics:synthetic-turbine-grid",
        license_id="NOASSERTION",
        source_sha256="1" * 64,
        speed_unit="caller-corrected-speed",
        pressure_ratio_convention="inlet-over-exit-total-pressure",
        corrected_mass_flow_basis="kg/s at caller-declared turbine correction reference",
        corrected_speed=(0.5, 1.0),
        expansion_pressure_ratio=(7.0, 8.5),
        corrected_mass_flow_kg_s=((1.0, 1.0), (1.0, 1.0)),
        isentropic_efficiency=((0.84, 0.86), (0.88, 0.90)),
    )
    air_flow = 1.0 / (1.0 + cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
    inputs = MapMatchedBraytonInputs(
        cycle_inputs=cycle_inputs,
        compressor_map=compressor_map,
        compressor_corrected_speed=0.75,
        compressor_pressure_ratio=8.0,
        compressor_actual_to_corrected_flow_factor=1.0 / air_flow,
        turbine_map=turbine_map,
        turbine_corrected_speed=0.75,
        turbine_actual_to_corrected_flow_factor=1.0,
        air_mass_flow_kg_s=air_flow,
        speed_link_evidence_id="synthetic-common-speed-basis",
        compressor_flow_evidence_id="synthetic-compressor-flow-correction",
        turbine_flow_evidence_id="synthetic-turbine-flow-correction",
    )
    result = run_map_matched_brayton(ct.Solution("gri30.yaml"), inputs)
    result.require_current()
    assert result.turbine_run.cycle_run.inputs.compressor_isentropic_efficiency == 0.85
    expected_turbine_efficiency = result.turbine_run.map_point.isentropic_efficiency
    assert result.turbine_run.cycle_run.inputs.turbine_isentropic_efficiency == expected_turbine_efficiency
    assert result.shaft_ledger.shaft_residual_w == (
        result.turbine_run.turbine_gross_power_w
        - result.turbine_run.compressor_power_w
    )
    assert result.inputs.speed_link_evidence_id == "synthetic-common-speed-basis"

    rejected = 0
    for query in (
        lambda: interpolate_compressor_map(
            compressor_map, corrected_speed=1.01, compression_pressure_ratio=8.0),
        lambda: interpolate_compressor_map(
            compressor_map, corrected_speed=0.75, compression_pressure_ratio=5.99),
        lambda: replace(inputs, compressor_actual_to_corrected_flow_factor=1.1),
    ):
        try:
            query()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Out-of-domain or flow-inconsistent map input was admitted")

    forged_rejected = 0
    try:
        MapMatchedBraytonRun(inputs, result.compressor_point, result.turbine_run,
                             result.shaft_ledger, object())
    except ValueError:
        forged_rejected += 1
    else:
        raise AssertionError("Direct map-matched result fabrication was admitted")

    original_efficiency = compressor_map.isentropic_efficiency
    object.__setattr__(compressor_map, "isentropic_efficiency", ((0.81, 0.83), (0.85, 0.87)))
    try:
        result.require_current()
    except ValueError:
        forged_rejected += 1
    else:
        raise AssertionError("Map mutation retained its previous result receipt")
    finally:
        object.__setattr__(compressor_map, "isentropic_efficiency", original_efficiency)
    compressor_map.require_current()
    assert rejected == 3 and forged_rejected == 2
    return ValidationOutcome(True, {
        "compressor_map_efficiency": result.compressor_point.isentropic_efficiency,
        "turbine_map_efficiency": expected_turbine_efficiency,
        "compressor_corrected_flow_kg_s": result.compressor_point.corrected_mass_flow_kg_s,
        "air_mass_flow_kg_s": air_flow,
        "shaft_residual_w": result.shaft_ledger.shaft_residual_w,
        "map_domain_or_flow_mismatches_rejected": rejected,
        "forged_or_stale_result_rejected": forged_rejected,
    }, LIMITS)
