"""Deferred synthetic cases for the one-point compressor cooling-bleed boundary."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic Cantera mechanism and maps check boundary software only.",
    "One compressed-air bleed is mixed once at the turbine inlet; turbine blade film and staged cooling are absent.",
    "Map correction factors, corrected-speed relation, pressure drop and shaft terms remain caller evidence.",
    "A passing contract does not qualify a gas turbine or validate independent machine performance.",
)


def cases():
    return tuple(ValidationCase(
        identifier=identifier,
        profile="hydrogen-engine",
        entrypoint=__name__ + ":validate_cooled_brayton",
        parameters={"scenario": scenario},
        invariants=invariants,
    ) for identifier, scenario, invariants in (
        ("hydrogen-brayton-compressor-bleed-zero-limit", "zero-bleed",
         ("zero-bleed-recovers-primary-flow", "compressor-and-turbine-map-points-bind",
          "shaft-and-stream-ledgers-close")),
        ("hydrogen-brayton-compressor-bleed-mixed-turbine", "positive-bleed",
         ("bleed-is-removed-before-combustion-and-added-once-before-turbine",
          "mass-energy-species-and-elemental-balances-close", "explicit-speed-flow-and-pressure-evidence")),
        ("hydrogen-brayton-cooling-pressure-rejection", "bad-pressure-drop",
         ("cooling-path-pressure-drop-must-match-injection-station",)),
        ("hydrogen-brayton-cooling-speed-link-rejection", "bad-speed-link",
         ("corrected-speed-link-is-numeric-and-evidence-bound",)),
    ))


def validate_cooled_brayton(*, work_directory, scenario="positive-bleed", **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.combustion.cooled_brayton import CoolingBleedInputs, run_cooled_brayton_point
    from h2physics.combustion.compressor_map import CompressorComponentMap
    from h2physics.combustion.open_brayton import OpenBraytonInputs
    from h2physics.combustion.turbine_map import TurbineComponentMap

    pressure_ratio = 8.
    recovery = .97
    air_flow, fuel_flow = 1., .02
    speed, turbine_speed = .75, .75
    bleed = 0. if scenario == "zero-bleed" else .1
    compressor_map = CompressorComponentMap(
        map_id="synthetic-cooling-compressor", evidence_id="synthetic:comp:v1",
        source_uri="urn:h2physics:synthetic:cooling-compressor", license_id="NOASSERTION",
        source_sha256="0" * 64, speed_unit="synthetic-corrected-speed",
        pressure_ratio_convention="outlet-over-inlet-total-pressure",
        corrected_mass_flow_basis="synthetic corrected kg/s at stated reference",
        corrected_speed=(.5, 1.), compression_pressure_ratio=(6., 10.),
        corrected_mass_flow_kg_s=((air_flow, air_flow), (air_flow, air_flow)),
        isentropic_efficiency=((.85, .85), (.85, .85)),
    )
    turbine_map = TurbineComponentMap(
        map_id="synthetic-cooling-turbine", evidence_id="synthetic:turbine:v1",
        source_uri="urn:h2physics:synthetic:cooling-turbine", license_id="NOASSERTION",
        source_sha256="1" * 64, speed_unit="synthetic-corrected-speed",
        pressure_ratio_convention="inlet-over-exit-total-pressure",
        corrected_mass_flow_basis="synthetic corrected kg/s at stated reference",
        corrected_speed=(.5, 1.), expansion_pressure_ratio=(7.5, 8.5),
        corrected_mass_flow_kg_s=((air_flow + fuel_flow, air_flow + fuel_flow),
                                  (air_flow + fuel_flow, air_flow + fuel_flow)),
        isentropic_efficiency=((.86, .86), (.86, .86)),
    )
    cycle = OpenBraytonInputs(
        mechanism_id="gri30.yaml-synthetic-cooling-contract",
        process_window_id="synthetic-cooling-bleed-point",
        air_temperature_k=288.15, air_pressure_pa=101325.,
        air_mole_fractions=(("O2", .21), ("N2", .79)),
        compressor_pressure_ratio=pressure_ratio, compressor_isentropic_efficiency=.85,
        combustor_pressure_recovery=recovery, hydrogen_fuel_to_air_mass_ratio=fuel_flow / air_flow,
        hydrogen_inlet_temperature_k=298.15, turbine_exhaust_pressure_pa=101325.,
        turbine_isentropic_efficiency=.86, hydrogen_lhv_j_kg=120e6,
        air_state_evidence_id="synthetic:air", hydrogen_feed_evidence_id="synthetic:h2",
        machine_parameter_evidence_id="synthetic:maps", lhv_evidence_id="synthetic:lhv",
    )
    comp_pressure = cycle.air_pressure_pa * pressure_ratio
    turbine_inlet = comp_pressure * recovery
    declared_drop = comp_pressure - turbine_inlet
    if scenario == "bad-pressure-drop":
        declared_drop += 1000.
    if scenario == "bad-speed-link":
        turbine_speed = .8
    try:
        inputs = CoolingBleedInputs(
            cycle_inputs=cycle, compressor_map=compressor_map, turbine_map=turbine_map,
            compressor_corrected_speed=speed, compressor_pressure_ratio=pressure_ratio,
            turbine_corrected_speed=turbine_speed, turbine_to_compressor_corrected_speed_ratio=1.,
            compressor_actual_to_corrected_flow_factor=1.,
            turbine_actual_to_corrected_flow_factor=1., air_mass_flow_kg_s=air_flow,
            hydrogen_mass_flow_kg_s=fuel_flow, cooling_air_fraction=bleed,
            cooling_line_pressure_drop_pa=declared_drop, shaft_mechanical_loss_w=0.,
            shaft_power_target_w=0., speed_link_evidence_id="synthetic:speed-link-v1",
            compressor_flow_evidence_id="synthetic:compressor-flow-v1",
            turbine_flow_evidence_id="synthetic:turbine-flow-v1",
            hydrogen_mass_flow_evidence_id="synthetic:hydrogen-flow-v1",
            cooling_split_evidence_id="synthetic:cooling-split-v1",
            cooling_pressure_evidence_id="synthetic:cooling-pressure-v1",
            shaft_loss_evidence_id="synthetic:zero-loss-v1",
            shaft_target_evidence_id="synthetic:shaft-target-v1",
            flow_relative_tolerance=1e-8, flow_absolute_tolerance_kg_s=1e-8,
            energy_absolute_tolerance_w=1e-5,
        )
    except ValueError as error:
        if scenario not in {"bad-pressure-drop", "bad-speed-link"}:
            raise
        return ValidationOutcome(True, {"admission_rejected": str(error)}, LIMITS)
    if scenario in {"bad-pressure-drop", "bad-speed-link"}:
        raise AssertionError("Invalid cooling boundary admission unexpectedly succeeded")
    result = run_cooled_brayton_point(lambda: ct.Solution("gri30.yaml"), inputs)
    assert result.require_current() is result
    turbine_point = result.turbine_point
    assert turbine_point.require_current() is turbine_point
    original_efficiency = turbine_point.isentropic_efficiency
    object.__setattr__(turbine_point, "isentropic_efficiency", original_efficiency + 0.01)
    try:
        turbine_point.require_current()
    except ValueError:
        turbine_point_mutation_rejected = True
    else:
        raise AssertionError("A changed turbine map point passed its freshness check")
    finally:
        object.__setattr__(turbine_point, "isentropic_efficiency", original_efficiency)
    assert result.require_current() is result
    assert abs(result.compressor_flow_residual_kg_s) <= inputs.flow_absolute_tolerance_kg_s
    assert abs(result.turbine_flow_residual_kg_s) <= inputs.flow_absolute_tolerance_kg_s
    assert abs(result.mix_energy_residual_w) <= inputs.energy_absolute_tolerance_w
    assert abs(result.shaft_residual_w - (
        result.turbine_power_w - result.compressor_power_w)) < 1e-8
    assert result.turbine_gas_mass_flow_kg_s == air_flow + fuel_flow
    assert result.primary_air_mass_flow_kg_s == air_flow * (1. - bleed)
    assert result.cooling_air_mass_flow_kg_s == air_flow * bleed
    if bleed == 0.:
        assert result.primary_air_mass_flow_kg_s == air_flow
    return ValidationOutcome(True, {
        "compressor_power_w": result.compressor_power_w,
        "turbine_power_w": result.turbine_power_w,
        "turbine_map_point_mutation_rejected": turbine_point_mutation_rejected,
        "shaft_residual_w": result.shaft_residual_w,
        "cooling_air_mass_flow_kg_s": result.cooling_air_mass_flow_kg_s,
        "mix_energy_residual_w": result.mix_energy_residual_w,
        "elemental_mass_residuals_kg_s": dict(result.elemental_mass_residuals_kg_s),
    }, LIMITS)
