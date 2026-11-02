"""Deferred contracts for the staged compressor-air injection boundary."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic Cantera states and caller inputs check contract behavior only.",
    "Each stage uses a lumped, frozen-composition expansion followed by perfect mixing.",
    "Coolant heat pickup is caller supplied; no blade metal, passage, film or flow-capacity physics is solved.",
    "No real turbine map qualification or independent experimental comparison has run.",
)


def cases():
    return tuple(ValidationCase(
        identifier=identifier,
        profile="hydrogen-engine",
        entrypoint=__name__ + ":validate_staged_turbine_cooling",
        parameters={"scenario": scenario},
        invariants=invariants,
    ) for identifier, scenario, invariants in (
        ("hydrogen-brayton-staged-cooling-ledger", "nominal",
         ("successive-stage-pressure-and-mass-flow-close",
          "coolant-heat-pickup-and-mixing-enthalpy-are-retained",
          "stage-mixing-energy-residual-is-bounded-relative-to-stream-enthalpy-power",
          "Cantera-owns-each-frozen-expansion-state")),
        ("hydrogen-brayton-staged-cooling-pressure-rejection", "bad-pressure",
         ("stage-pressures-must-descend-and-terminate-at-exhaust",)),
        ("hydrogen-brayton-staged-cooling-evidence-rejection", "missing-evidence",
         ("each-stage-coolant-flow-requires-source-identity",)),
    ))


def validate_staged_turbine_cooling(*, work_directory, scenario="nominal", **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.combustion.open_brayton import OpenBraytonInputs, run_open_cycle_brayton
    from h2physics.combustion.staged_turbine_cooling import (
        StagedTurbineCoolingInputs, run_staged_turbine_cooling)

    total_air, hydrogen = 1.0, 0.02
    coolant = (0.04, 0.06)
    primary_air = total_air - sum(coolant)
    cycle = OpenBraytonInputs(
        mechanism_id="gri30.yaml-synthetic-staged-cooling",
        process_window_id="synthetic-staged-turbine-point",
        air_temperature_k=288.15, air_pressure_pa=101325.0,
        air_mole_fractions=(("O2", 0.21), ("N2", 0.79)),
        compressor_pressure_ratio=8.0, compressor_isentropic_efficiency=0.85,
        combustor_pressure_recovery=0.97,
        hydrogen_fuel_to_air_mass_ratio=hydrogen / primary_air,
        hydrogen_inlet_temperature_k=298.15,
        turbine_exhaust_pressure_pa=101325.0,
        turbine_isentropic_efficiency=0.86, hydrogen_lhv_j_kg=120e6,
        air_state_evidence_id="synthetic:air", hydrogen_feed_evidence_id="synthetic:h2",
        machine_parameter_evidence_id="synthetic:machine", lhv_evidence_id="synthetic:lhv",
    )
    # The open-cycle API receives an already-created native phase. Only the
    # staged-cooling API below accepts a phase factory, because it must retain
    # an independent phase from the original Brayton result.
    brayton = run_open_cycle_brayton(ct.Solution("gri30.yaml"), cycle)
    hot_pressure = brayton.states[3].pressure_pa
    pressures = (500000.0, cycle.turbine_exhaust_pressure_pa)
    ids = ("synthetic:stage-1", "synthetic:stage-2")
    if scenario == "bad-pressure":
        pressures = (500000.0, hot_pressure)
    elif scenario == "missing-evidence":
        ids = ("synthetic:stage-1", "")
    try:
        inputs = StagedTurbineCoolingInputs(
            brayton=brayton, air_mass_flow_kg_s=total_air,
            hydrogen_mass_flow_kg_s=hydrogen,
            stage_exit_pressures_pa=pressures,
            stage_isentropic_efficiencies=(0.9, 0.88),
            coolant_mass_flow_kg_s=coolant,
            coolant_heat_pickup_j_kg=(12000.0, 18000.0), evidence_ids=ids,
            pressure_basis_evidence_id="synthetic:stage-pressure-basis",
            efficiency_evidence_id="synthetic:stage-efficiencies",
            feed_evidence_id="synthetic:bleed-feed-schedule",
        )
    except ValueError as error:
        if scenario not in {"bad-pressure", "missing-evidence"}:
            raise
        return ValidationOutcome(True, {"admission_rejected": str(error)}, LIMITS)
    if scenario in {"bad-pressure", "missing-evidence"}:
        raise AssertionError("Invalid staged-cooling inputs were admitted")
    result = run_staged_turbine_cooling(lambda: ct.Solution("gri30.yaml"), inputs)
    assert result.require_current() is result
    assert len(result.stages) == 2
    assert abs(result.initial_mass_flow_kg_s - (primary_air + hydrogen)) < 1e-12
    assert abs(result.final_mass_flow_kg_s - (total_air + hydrogen)) < 1e-12
    assert abs(result.coolant_heat_pickup_w - (0.04 * 12000.0 + 0.06 * 18000.0)) < 1e-9
    assert all(stage.pressure_out_pa < stage.pressure_in_pa for stage in result.stages)
    assert abs(result.turbine_power_w - sum(stage.shaft_power_w for stage in result.stages)) < 1e-8
    assert abs(result.energy_residual_w) < 1e-7 * max(abs(result.turbine_power_w), 1.0)
    assert all(abs(stage.mixing_energy_residual_w) <= 1e-7 * max(
        abs(stage.mass_flow_out_kg_s * stage.mixed_outlet.enthalpy_j_kg),
        abs(stage.mass_flow_in_kg_s * stage.expansion_outlet.enthalpy_j_kg),
        abs(stage.coolant_mass_flow_kg_s * stage.coolant_enthalpy_j_kg), 1.0,
    ) for stage in result.stages)
    return ValidationOutcome(True, {
        "stage_power_w": tuple(stage.shaft_power_w for stage in result.stages),
        "initial_mass_flow_kg_s": result.initial_mass_flow_kg_s,
        "final_mass_flow_kg_s": result.final_mass_flow_kg_s,
        "coolant_heat_pickup_w": result.coolant_heat_pickup_w,
        "energy_residual_w": result.energy_residual_w,
        "exhaust_temperature_k": result.exhaust.temperature_k,
    }, LIMITS)
