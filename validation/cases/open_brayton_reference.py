"""Deferred acceptance definitions for the optional open Brayton reference."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Native Cantera ideal-gas properties and HP equilibrium own the gas states.",
    "This is a single-point reference; efficiencies are caller parameters, not maps.",
    "No mechanical/generator losses, fuel compression, cooling bleed, transient control, or qualification.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-brayton-reference",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_reference",
            invariants=(
                "native-hp-equilibrium", "frozen-expansion-composition",
                "compressor-and-turbine-work-signs", "elemental-balance",
                "open-cycle-first-law-closure",
                "mass-specific Cantera state quantities reject a molar-basis phase before state-pair assignments",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-input-guards",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_input_guards",
            invariants=(
                "strict-composition-normalization", "compressor-ratio-domain",
                "efficiency-bounds", "pressure-order", "source-identities",
                "oxygen-bearing-oxidizer", "direct-state-species-element-basis",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-summary-integrity",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_summary_integrity",
            invariants=(
                "reconstruct-work-ledgers", "reconstruct-energy-residuals",
                "reconstruct-element-residuals", "native-terminal-state-binding",
                "native-species-thermo-reaction-and-multiplier-seal", "native-run-issuer",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-turbine-map-boundary",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_turbine_map_boundary",
            invariants=(
                "map-efficiency-feeds-native-expansion",
                "cycle-total-pressure-ratio-matches-map-point",
                "actual-and-corrected-turbine-flow-close",
                "explicit-flow-conversion-evidence-retained",
                "exact-cycle-input-identity-retained",
                "no-map-or-flow-extrapolation",
                "mass-flow-scaled-compressor-turbine-and-net-gas-path-power",
                "explicit-shaft-loss-and-generator-conversion",
                "shaft-and-electric-power-ledger-recomputed",
                "shaft-deficit-rejected",
                "external-compressor-point-requires-matching-process-window-and-flow",
                "compressor-turbine-shaft-residual-recomputed",
                "compressor-process-window-mismatch-rejected",
                "compressor-air-flow-basis-mismatch-rejected",
            ),
        ),
    )


def _inputs(**overrides):
    from h2physics.combustion import OpenBraytonInputs

    values = dict(
        mechanism_id="cantera-gri30-deferred-example",
        process_window_id="steady-point-a",
        air_temperature_k=288.15,
        air_pressure_pa=101325.0,
        air_mole_fractions=(("O2", 0.21), ("N2", 0.79)),
        compressor_pressure_ratio=8.0,
        compressor_isentropic_efficiency=0.86,
        combustor_pressure_recovery=0.97,
        hydrogen_fuel_to_air_mass_ratio=0.02,
        hydrogen_inlet_temperature_k=298.15,
        turbine_exhaust_pressure_pa=101325.0,
        turbine_isentropic_efficiency=0.88,
        hydrogen_lhv_j_kg=120.0e6,
        air_state_evidence_id="authored-air-boundary",
        hydrogen_feed_evidence_id="authored-h2-boundary",
        machine_parameter_evidence_id="authored-point-parameters",
        lhv_evidence_id="authored-lhv-basis",
    )
    values.update(overrides)
    return OpenBraytonInputs(**values)


def validate_reference(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.combustion import run_open_cycle_brayton

    phase = ct.Solution("gri30.yaml")
    result = run_open_cycle_brayton(phase, _inputs())
    assert result.native_phase is phase
    assert [state.station for state in result.states] == [
        "air_inlet", "compressor_outlet", "hydrogen_feed",
        "combustor_outlet", "turbine_exhaust",
    ]
    assert result.states[1].pressure_pa > result.states[0].pressure_pa
    assert result.states[3].pressure_pa < result.states[1].pressure_pa
    assert result.states[4].pressure_pa == result.inputs.turbine_exhaust_pressure_pa
    assert result.compressor_work_j_kg_air > 0.0
    assert result.turbine_work_j_kg_air > 0.0
    assert max(abs(value) for _, value in result.elemental_mass_residuals) < 1e-9
    scale = max(abs(state.enthalpy_j_kg) for state in result.states)
    assert abs(result.combustor_enthalpy_residual_j_kg_air) < 1e-7 * scale
    assert abs(result.open_cycle_energy_residual_j_kg_air) < 1e-7 * scale
    return ValidationOutcome(
        True,
        {
            "compressor_work_j_kg_air": result.compressor_work_j_kg_air,
            "turbine_work_j_kg_air": result.turbine_work_j_kg_air,
            "net_work_j_kg_air": result.net_work_j_kg_air,
            "thermal_efficiency": result.thermal_efficiency,
            "maximum_element_mass_residual": max(abs(value) for _, value in result.elemental_mass_residuals),
        },
        LIMITS,
    )


def validate_input_guards(*, work_directory, **parameters):
    del work_directory, parameters
    rejected = 0
    for change in (
        {"compressor_pressure_ratio": 1.0},
        {"compressor_isentropic_efficiency": 1.01},
        {"air_mole_fractions": (("O2", 0.21), ("N2", 0.78))},
        {"turbine_exhaust_pressure_pa": 1.0e6},
        {"process_window_id": " "},
        {"air_mole_fractions": (("N2", 1.0),)},
    ):
        try:
            _inputs(**change)
        except (TypeError, ValueError):
            rejected += 1
    from h2physics.combustion import BraytonGasState

    try:
        BraytonGasState(
            station="air_inlet",
            temperature_k=288.15,
            pressure_pa=101325.0,
            enthalpy_j_kg=0.0,
            entropy_j_kg_k=0.0,
            species_names=("O2", "N2"),
            mass_fractions=(0.23, 0.77),
            elemental_mass_fractions=(("O", 0.2), ("N", 0.2)),
            mechanism_id="test-mechanism",
            process_window_id="test-point",
        )
    except ValueError:
        rejected += 1
    assert rejected == 7
    return ValidationOutcome(True, {"rejected_inputs": rejected}, LIMITS)


def validate_summary_integrity(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import cantera as ct

    from h2physics.combustion import OpenBraytonRun, run_open_cycle_brayton

    result = run_open_cycle_brayton(ct.Solution("gri30.yaml"), _inputs())
    direct_rejected = 0
    try:
        OpenBraytonRun(
            inputs=result.inputs,
            states=result.states,
            elemental_mass_residuals=result.elemental_mass_residuals,
            compressor_work_j_kg_air=result.compressor_work_j_kg_air,
            turbine_work_j_kg_air=result.turbine_work_j_kg_air,
            net_work_j_kg_air=result.net_work_j_kg_air,
            hydrogen_heat_input_j_kg_air=result.hydrogen_heat_input_j_kg_air,
            thermal_efficiency=result.thermal_efficiency,
            combustor_enthalpy_residual_j_kg_air=result.combustor_enthalpy_residual_j_kg_air,
            open_cycle_energy_residual_j_kg_air=result.open_cycle_energy_residual_j_kg_air,
            native_phase=result.native_phase,
            _mechanism_signature=result._mechanism_signature,
        )
    except ValueError:
        direct_rejected = 1
    else:
        raise AssertionError("Direct OpenBraytonRun construction forged native run evidence")
    forged = (
        ("compressor_work_j_kg_air", result.compressor_work_j_kg_air + 1.0),
        ("turbine_work_j_kg_air", result.turbine_work_j_kg_air + 1.0),
        ("net_work_j_kg_air", result.net_work_j_kg_air + 1.0),
        ("hydrogen_heat_input_j_kg_air", result.hydrogen_heat_input_j_kg_air + 1.0),
        ("thermal_efficiency", result.thermal_efficiency + 1e-3),
        ("combustor_enthalpy_residual_j_kg_air", result.combustor_enthalpy_residual_j_kg_air + 1.0),
        ("open_cycle_energy_residual_j_kg_air", result.open_cycle_energy_residual_j_kg_air + 1.0),
    )
    rejected = 0
    for field, value in forged:
        try:
            replace(result, **{field: value})
        except ValueError:
            rejected += 1
    elements = list(result.elemental_mass_residuals)
    name, residual = elements[0]
    elements[0] = (name, residual + 1e-4)
    try:
        replace(result, elemental_mass_residuals=tuple(elements))
    except ValueError:
        rejected += 1
    phase = result.native_phase
    phase.TP = phase.T + 1.0, phase.P
    try:
        replace(result, native_phase=phase)
    except (TypeError, ValueError):
        rejected += 1
    if phase.n_reactions:
        original_multiplier = phase.multiplier(0)
        phase.set_multiplier(original_multiplier * 0.5, 0)
        try:
            replace(result, native_phase=phase)
        except (TypeError, ValueError):
            rejected += 1
        else:
            raise AssertionError("Changed native reaction multiplier remained covered by the cycle receipt")
        finally:
            phase.set_multiplier(original_multiplier, 0)
    assert rejected == len(forged) + 2 + bool(phase.n_reactions) + direct_rejected
    return ValidationOutcome(True, {"forged_summaries_rejected": rejected}, LIMITS)


def validate_turbine_map_boundary(*, work_directory, **parameters):
    """Deferred native cycle/map match; never run during local source work."""
    del work_directory, parameters
    from dataclasses import replace

    import cantera as ct

    from h2physics.combustion import (
        CompressorOperatingPoint,
        MapBoundBraytonInputs,
        ShaftPowerBalanceInputs,
        TurbineComponentMap,
        balance_map_bound_brayton_shaft,
        couple_compressor_to_map_bound_brayton,
        interpolate_turbine_map,
        run_map_bound_open_cycle_brayton,
    )

    cycle_inputs = _inputs()
    pressure_ratio = (
        cycle_inputs.air_pressure_pa * cycle_inputs.compressor_pressure_ratio
        * cycle_inputs.combustor_pressure_recovery
        / cycle_inputs.turbine_exhaust_pressure_pa
    )
    component_map = TurbineComponentMap(
        map_id="deferred-map-bound-cycle",
        evidence_id="deferred-map-bound-cycle-source",
        source_uri="urn:h2physics:deferred-map-bound-fixture",
        license_id="NOASSERTION",
        source_sha256="0" * 64,
        speed_unit="corrected-rpm",
        pressure_ratio_convention="inlet-over-exit-total-pressure",
        corrected_mass_flow_basis="kg/s at declared correction reference",
        corrected_speed=(0.5, 1.0),
        expansion_pressure_ratio=(pressure_ratio - 1.0, pressure_ratio + 1.0),
        corrected_mass_flow_kg_s=((0.5, 0.7), (0.6, 0.8)),
        isentropic_efficiency=((0.7, 0.76), (0.78, 0.84)),
    )
    speed = 0.75
    point = interpolate_turbine_map(
        component_map, corrected_speed=speed,
        expansion_pressure_ratio=pressure_ratio,
    )
    correction = 0.92
    air_flow = point.corrected_mass_flow_kg_s / (
        correction * (1.0 + cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
    )
    inputs = MapBoundBraytonInputs(
        cycle_inputs=cycle_inputs,
        component_map=component_map,
        corrected_speed=speed,
        air_mass_flow_kg_s=air_flow,
        actual_to_corrected_flow_factor=correction,
        speed_link_evidence_id="fixture-speed-basis-link",
        flow_conversion_evidence_id="fixture-flow-correction-link",
    )
    result = run_map_bound_open_cycle_brayton(ct.Solution("gri30.yaml"), inputs)
    result.require_current()
    assert result.map_point.component_map is component_map
    assert result.cycle_run.inputs.turbine_isentropic_efficiency == point.isentropic_efficiency
    assert result.corrected_turbine_mass_flow_kg_s == point.corrected_mass_flow_kg_s
    assert result.compressor_power_w == (
        result.cycle_run.compressor_work_j_kg_air * inputs.air_mass_flow_kg_s
    )
    assert result.turbine_gross_power_w == (
        result.cycle_run.turbine_work_j_kg_air * inputs.air_mass_flow_kg_s
    )
    assert result.net_gas_path_power_w == (
        result.cycle_run.net_work_j_kg_air * inputs.air_mass_flow_kg_s
    )
    assert result.net_gas_path_power_w == (
        result.turbine_gross_power_w - result.compressor_power_w
    )
    compressor_point = CompressorOperatingPoint(
        operating_point_id=cycle_inputs.process_window_id,
        process_window_id=cycle_inputs.process_window_id,
        evidence_id="fixture-compressor-point",
        shaft_speed_link_evidence_id="fixture-common-speed-link",
        flow_link_evidence_id="fixture-common-flow-link",
        specific_work_j_kg_air=result.cycle_run.compressor_work_j_kg_air,
        inlet_air_mass_flow_kg_s=air_flow,
    )
    coupled = couple_compressor_to_map_bound_brayton(result, compressor_point)
    coupled.require_current()
    assert abs(coupled.shaft_residual_w) < 1e-8
    rejected_window = False
    try:
        couple_compressor_to_map_bound_brayton(
            result, replace(compressor_point, process_window_id="different-window"))
    except ValueError:
        rejected_window = True
    assert rejected_window
    rejected_flow = False
    try:
        couple_compressor_to_map_bound_brayton(
            result, replace(compressor_point, inlet_air_mass_flow_kg_s=air_flow * 1.1))
    except ValueError:
        rejected_flow = True
    assert rejected_flow
    balance_inputs = ShaftPowerBalanceInputs(
        cycle_run=result,
        shaft_mechanical_loss_w=0.02 * result.net_gas_path_power_w,
        generator_efficiency=0.96,
        loss_evidence_id="fixture-shaft-loss",
        generator_evidence_id="fixture-generator-efficiency",
    )
    balance = balance_map_bound_brayton_shaft(balance_inputs)
    balance.require_current()
    assert balance.shaft_net_power_w == balance.gas_path_net_power_w - balance_inputs.shaft_mechanical_loss_w
    assert balance.electric_power_w == balance.shaft_net_power_w * balance_inputs.generator_efficiency
    rejected_deficit = False
    try:
        balance_map_bound_brayton_shaft(replace(balance_inputs, shaft_mechanical_loss_w=1e100))
    except ValueError:
        rejected_deficit = True
    assert rejected_deficit
    rejected_efficiency = False
    try:
        replace(balance_inputs, generator_efficiency=1.01)
    except ValueError:
        rejected_efficiency = True
    assert rejected_efficiency
    altered_cycle_inputs = replace(
        result.cycle_run.inputs, air_state_evidence_id="forged-air-evidence")
    altered_cycle = replace(result.cycle_run, inputs=altered_cycle_inputs)
    rejected_relabel = False
    try:
        replace(result, cycle_run=altered_cycle)
    except ValueError:
        rejected_relabel = True
    assert rejected_relabel
    return ValidationOutcome(True, {
        "map_evidence_id": component_map.evidence_id,
        "mapped_turbine_efficiency": point.isentropic_efficiency,
        "actual_turbine_mass_flow_kg_s": result.actual_turbine_mass_flow_kg_s,
        "corrected_turbine_mass_flow_kg_s": result.corrected_turbine_mass_flow_kg_s,
        "cycle_net_work_j_kg_air": result.cycle_run.net_work_j_kg_air,
        "compressor_power_w": result.compressor_power_w,
        "turbine_gross_power_w": result.turbine_gross_power_w,
        "net_gas_path_power_w": result.net_gas_path_power_w,
        "shaft_net_power_w": balance.shaft_net_power_w,
        "electric_power_w": balance.electric_power_w,
        "shaft_deficit_rejected": rejected_deficit,
        "invalid_generator_efficiency_rejected": rejected_efficiency,
        "cycle_input_relabel_rejected": rejected_relabel,
    }, (
        *LIMITS,
        "The flow correction factor is caller-evidenced and is not inferred from generic map metadata.",
        "The mapped reference remains single-point and has no compressor map or shaft solution.",
    ))
