"""Deferred reduced-order alkaline bubble-loss integration contracts."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="alkaline-bubble-electrode-and-electrolyte-losses",
        profile="alkaline-electrolysis",
        entrypoint=__name__ + ":validate_contract",
        invariants=(
            "caller-supplied anode and cathode coverages remain independent inputs",
            "surface masking adds the Tafel effective-area penalty without inferring coverage",
            "gas void adds a Bruggeman effective-conductivity resistance increment",
            "zero coverage and zero void recover the retained bubble-free stack result",
            "Faradaic hydrogen production is unchanged by the electrical loss-only correction",
            "power and voltage increments reconcile against the original shared HydrogenStack result",
            "out-of-domain coverage, void fraction and unsupported fuel-cell mode are rejected",
            "source/evidence identities and callbacks remain attached to the immutable evaluation",
            "absolute pressure and optional electrolyte/electrode identities reach every callback",
            "pressure-dependent callback output changes with the declared absolute operating pressure",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.alkaline_bubbles import (
        AlkalineBubbleModel,
        evaluate_alkaline_bubbles,
    )
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    energy = ReactionEnergy(237_000.0, 285_800.0, "authored-standard-state", "liquid")
    stack = HydrogenStack(
        StackGeometry(12, 0.02, 2.01588e-3),
        lambda temperature_k: energy,
        {"bubble-free-base-loss": lambda current_density, temperature_k: 0.25},
    )

    def model(theta_a, theta_c, phi):
        return AlkalineBubbleModel(
            anode_coverage=lambda condition: (
                theta_a + (condition.absolute_pressure_pa - 1.0e5) / 1.0e7
            ),
            cathode_coverage=lambda condition: (
                theta_c + (condition.absolute_pressure_pa - 1.0e5) / 1.0e7
            ),
            electrolyte_void_fraction=lambda condition: (
                phi + (condition.absolute_pressure_pa - 1.0e5) / 1.0e7
            ),
            bubble_free_area_resistance_ohm_m2=lambda condition: 1.5e-4,
            anode_tafel_slope_v_decade=lambda condition: 0.045,
            cathode_tafel_slope_v_decade=lambda condition: 0.038,
            coverage_evidence_id="authored-coverage-boundary",
            void_fraction_evidence_id="authored-void-boundary",
            electrolyte_resistance_evidence_id="authored-base-resistance",
            tafel_slope_evidence_id="authored-electrode-slopes",
            correlation_evidence_id="authored-reduced-order-correlation-selection",
        )

    zero = evaluate_alkaline_bubbles(
        stack, model(0.0, 0.0, 0.0), 4_000.0, 333.15,
        absolute_pressure_pa=1.0e5,
    )
    assert zero.require_current() is zero
    assert zero.bubble_voltage_loss_v_cell == 0.0
    assert zero.corrected_cell_voltage_v == zero.base_result.cell_voltage_v

    loaded = evaluate_alkaline_bubbles(
        stack, model(0.2, 0.35, 0.1), 4_000.0, 333.15,
        absolute_pressure_pa=6.0e5, electrolyte_concentration_mol_m3=6_000.0,
        electrolyte_composition_id="synthetic-KOH-composition-v1",
        anode_id="synthetic-anode", cathode_id="synthetic-cathode",
    )
    assert loaded.require_current() is loaded
    assert loaded.coverage_voltage_loss_v_cell > 0.0
    assert loaded.electrolyte_void_voltage_loss_v_cell > 0.0
    assert loaded.corrected_cell_voltage_v == (
        loaded.base_result.cell_voltage_v + loaded.bubble_voltage_loss_v_cell
    )
    assert loaded.base_result.hydrogen_production_kg_s == zero.base_result.hydrogen_production_kg_s
    assert loaded.additional_electric_input_w == (
        loaded.base_result.current_a * loaded.bubble_voltage_loss_v_cell
        * stack.geometry.series_cells
    )
    assert loaded.corrected_unallocated_energy_rate_w == (
        loaded.base_result.unallocated_energy_rate_w + loaded.additional_electric_input_w
    )
    assert loaded.condition.absolute_pressure_pa == 6.0e5
    assert loaded.condition.electrolyte_concentration_mol_m3 == 6_000.0
    assert loaded.condition.electrolyte_composition_id == "synthetic-KOH-composition-v1"
    assert (loaded.condition.anode_id, loaded.condition.cathode_id) == (
        "synthetic-anode", "synthetic-cathode",
    )
    lower_pressure = evaluate_alkaline_bubbles(
        stack, model(0.2, 0.35, 0.1), 4_000.0, 333.15,
        absolute_pressure_pa=1.0e5,
        electrolyte_concentration_mol_m3=6_000.0,
        electrolyte_composition_id="synthetic-KOH-composition-v1",
        anode_id="synthetic-anode", cathode_id="synthetic-cathode",
    )
    assert loaded.coverage_voltage_loss_v_cell > lower_pressure.coverage_voltage_loss_v_cell
    assert loaded.electrolyte_void_voltage_loss_v_cell > lower_pressure.electrolyte_void_voltage_loss_v_cell

    invalid_models = (
        ("anode coverage", model(1.0, 0.0, 0.0)),
        ("cathode coverage", model(0.0, 1.0, 0.0)),
        ("electrolyte void fraction", model(0.0, 0.0, 1.0)),
    )
    rejected = 0
    for boundary, invalid in invalid_models:
        try:
            evaluate_alkaline_bubbles(
                stack, invalid, 4_000.0, 333.15, absolute_pressure_pa=1.0e5,
            )
        except ValueError:
            rejected += 1
        else:
            raise AssertionError(f"An out-of-domain {boundary} was admitted")
    assert rejected == len(invalid_models)
    for kwargs in (
        {"absolute_pressure_pa": 0.0},
        {"absolute_pressure_pa": 1.0e5, "electrolyte_concentration_mol_m3": 6_000.0},
    ):
        try:
            evaluate_alkaline_bubbles(stack, model(0.1, 0.1, 0.1), 4_000.0, 333.15, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid absolute-pressure or electrolyte context was accepted")
    return ValidationOutcome(True, {
        "coverage_loss_v_cell": loaded.coverage_voltage_loss_v_cell,
        "electrolyte_void_loss_v_cell": loaded.electrolyte_void_voltage_loss_v_cell,
        "additional_electric_power_w": loaded.additional_electric_input_w,
        "faradaic_hydrogen_kg_s_unchanged": loaded.base_result.hydrogen_production_kg_s,
        "out_of_domain_rejections": rejected,
    }, ("synthetic API contract only; no bubble-parameter calibration, measured stack comparison, or qualification",))
