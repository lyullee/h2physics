from dataclasses import replace

import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
from h2physics.thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalCycleError,
    ThermochemicalEvidence,
    ThermochemicalFeed,
    ThermochemicalInventory,
    ThermochemicalStage,
)


def fixture(*, gauge=0.0):
    species = (
        ChemicalSpecies("oxide", {"Fe": 3, "O": 4}, 0.232, "solid-oxide"),
        ChemicalSpecies("reduced", {"Fe": 1, "O": 1}, 0.072, "solid-reduced"),
        ChemicalSpecies("water", {"H": 2, "O": 1}, 0.018, "declared-vapor"),
        ChemicalSpecies("H2", {"H": 2}, 0.002, "declared-gas"),
        ChemicalSpecies("O2", {"O": 2}, 0.032, "declared-gas"),
    )
    capacities, formation = (
        (100.0, 30.0, 40.0, 29.0, 30.0),
        (-900000.0, -250000.0, -240000.0, 0.0, 0.0),
    )
    functions = tuple(
        (
            lambda t, p, c=c, h=h, s=s: (
                h
                + c * (t - 300.0)
                + gauge
                * (
                    s.elements.get("H", 0)
                    + 2 * s.elements.get("O", 0)
                    + 5 * s.elements.get("Fe", 0)
                )
            )
        )
        for c, h, s in zip(capacities, formation, species, strict=True)
    )
    provider = FunctionalMolarEnthalpy(
        species, functions, f"authored-caloric:{gauge}", (300.0, 1600.0), (1e4, 1e6)
    )
    evidence = ThermochemicalEvidence(
        "authored-cycle",
        "additive-phase-enthalpy",
        "prescribed-component-takeoff",
        "constant-P-required-heat",
        Origin.SYNTHETIC,
    )
    engine = FiniteThermochemicalCycle(provider, evidence)
    reduction = StoichiometricReaction("authored-reduction", species, (-1, 3, 0, 0, 0.5))
    oxidation = StoichiometricReaction("authored-steam-oxidation", species, (1, -3, -1, 1, 0))
    initial = ThermochemicalInventory({"oxide": 1.0}, 300.0, 1e5, provider.basis_id)
    feed = ThermochemicalFeed(
        ThermochemicalInventory({"water": 0.1}, 500.0, 1e5, provider.basis_id),
        "authored-steam",
        Origin.SYNTHETIC,
    )
    stages = (
        ThermochemicalStage(
            "reduce",
            100.0,
            110.0,
            "clock",
            1400.0,
            (PrescribedConversion(reduction, 0.1, "authored-extent"),),
            "authored-stage",
        ),
        ThermochemicalStage(
            "oxidize",
            110.0,
            120.0,
            "clock",
            900.0,
            (PrescribedConversion(oxidation, 0.1, "authored-extent"),),
            "authored-stage",
            feeds=(feed,),
            pre_withdrawal_mol={"O2": 0.05},
        ),
        ThermochemicalStage(
            "reset",
            120.0,
            130.0,
            "clock",
            300.0,
            (),
            "authored-stage",
            pre_withdrawal_mol={"H2": 0.1},
        ),
    )
    return engine, initial, stages


def test_finite_carrier_closes_with_explicit_steam_and_separate_hot_product_exports():
    engine, initial, stages = fixture()
    trace = engine.run(
        initial, stages, carrier_species=("oxide", "reduced"), require_full_inventory_closed=True
    )
    assert trace.carrier_closed and trace.temperature_closed and trace.full_inventory_closed
    assert trace.final.amounts_mol == pytest.approx(
        dict(initial.amounts_mol) | {"reduced": 0.0, "water": 0.0, "H2": 0.0, "O2": 0.0}
    )
    assert trace.feed_mol == pytest.approx([0.0, 0.0, 0.1, 0.0, 0.0])
    assert trace.exported_mol == pytest.approx([0.0, 0.0, 0.0, 0.1, 0.05])
    assert np.max(abs(trace.element_residual_mol)) < 1e-15
    assert abs(trace.mass_residual_kg) < 1e-16
    assert abs(trace.energy_residual_j) < 1e-9
    assert trace.enthalpy_provider is engine.enthalpy
    assert not trace.feed_mol.flags.writeable


def test_independent_caloric_arithmetic_includes_feed_conditioning_and_both_product_temperatures():
    engine, initial, stages = fixture()
    trace = engine.run(initial, stages, carrier_species=("oxide", "reduced"))
    # Hot O2 at1400K, H2 at900K and incoming steam at500K, in the authored basis.
    expected_net = (
        0.05 * 30 * (1400 - 300) + 0.1 * 29 * (900 - 300) - 0.1 * (-240000 + 40 * (500 - 300))
    )
    assert trace.net_heat_required_j == pytest.approx(expected_net, abs=1e-9)
    first = trace.steps[0]
    assert first.conditioning_heat_required_j == pytest.approx(100 * (1400 - 300))
    # ΔH at1400K of one mol reaction; finite extent .1mol.
    reaction_heat = 0.1 * (3 * (-250000 + 30 * 1100) + 0.5 * 30 * 1100 - (-900000 + 100 * 1100))
    assert first.reaction_heat_required_j == pytest.approx(reaction_heat)
    assert first.mean_required_heat_w == pytest.approx(first.heat_required_j / 10.0)
    assert trace.gross_heat_input_j - trace.gross_heat_rejection_j == pytest.approx(
        trace.net_heat_required_j
    )
    assert trace.gross_heat_input_j > trace.net_heat_required_j
    assert not hasattr(trace, "solar_efficiency")


def test_conserved_element_reference_shift_leaves_every_required_heat_unchanged():
    engine, initial, stages = fixture()
    trace = engine.run(initial, stages, carrier_species=("oxide", "reduced"))
    other, start, commands = fixture(gauge=1e6)
    shifted = other.run(start, commands, carrier_species=("oxide", "reduced"))
    np.testing.assert_allclose(
        [s.heat_required_j for s in trace.steps],
        [s.heat_required_j for s in shifted.steps],
        rtol=0,
        atol=1e-8,
    )


def test_heat_only_stages_are_explicit_and_do_not_invent_a_reaction_or_heat_recovery():
    engine, initial, _ = fixture()
    stages = (
        ThermochemicalStage("heat", 0.0, 1.0, "clock", 500.0, (), "authored"),
        ThermochemicalStage("cool", 1.0, 2.0, "clock", 300.0, (), "authored"),
    )
    trace = engine.run(
        initial, stages, carrier_species=("oxide",), require_full_inventory_closed=True
    )
    assert trace.gross_heat_input_j == pytest.approx(20000.0)
    assert trace.gross_heat_rejection_j == pytest.approx(20000.0)
    assert trace.net_heat_required_j == pytest.approx(0.0, abs=1e-9)
    assert all(not step.conversions for step in trace.steps)


def test_reused_native_caloric_buffer_cannot_erase_sensible_heat():
    from types import SimpleNamespace

    original, initial, _ = fixture()
    scratch = np.zeros(len(original.species))

    def enthalpies(temperature, pressure):
        scratch[:] = original.enthalpy.enthalpies_j_mol(temperature, pressure)
        return scratch

    cached = SimpleNamespace(
        species=original.species, basis_id=original.energy_basis_id, enthalpies_j_mol=enthalpies
    )
    engine = FiniteThermochemicalCycle(cached, original.evidence)
    stages = (
        ThermochemicalStage("hold", 0.0, 1.0, "clock", 300.0, (), "authored"),
        ThermochemicalStage("heat", 1.0, 2.0, "clock", 500.0, (), "authored"),
        ThermochemicalStage("cool", 2.0, 3.0, "clock", 300.0, (), "authored"),
    )
    trace = engine.run(
        initial, stages, carrier_species=("oxide",), require_full_inventory_closed=True
    )
    assert [s.heat_required_j for s in trace.steps] == pytest.approx([0.0, 20000.0, -20000.0])
    assert trace.gross_heat_input_j == pytest.approx(20000.0)
    assert trace.gross_heat_rejection_j == pytest.approx(20000.0)


def test_finite_amount_that_overflows_extensive_energy_is_rejected_with_stage():
    engine, initial, _ = fixture()
    huge = replace(initial, amounts_mol={"oxide": 1e308})
    stage = ThermochemicalStage("hold", 0.0, 1.0, "clock", 300.0, (), "authored")
    with pytest.raises(ThermochemicalCycleError, match="finite") as error:
        engine.run(huge, (stage,), carrier_species=("oxide",))
    assert error.value.before is huge and error.value.stage is stage
    assert not error.value.completed_steps and error.value.__cause__ is not None


def test_material_or_temperature_nonclosure_preserves_completed_trace():
    engine, initial, stages = fixture()
    with pytest.raises(ThermochemicalCycleError) as caught:
        engine.run(
            initial,
            stages[:1],
            carrier_species=("oxide", "reduced"),
            require_temperature_closed=False,
        )
    assert caught.value.trace is not None and not caught.value.trace.carrier_closed
    assert len(caught.value.completed_steps) == 1
    assert caught.value.provider is engine.enthalpy
    partial = engine.run(
        initial,
        stages[:1],
        carrier_species=("oxide", "reduced"),
        require_carrier_closed=False,
        require_temperature_closed=False,
    )
    assert not partial.carrier_closed and not partial.temperature_closed
    with pytest.raises(ThermochemicalCycleError):
        engine.run(initial, stages[:2], carrier_species=("oxide", "reduced"))


def test_full_inventory_is_separate_from_carrier_closure():
    engine, initial, stages = fixture()
    reset = replace(stages[-1], pre_withdrawal_mol={})
    trace = engine.run(initial, (*stages[:2], reset), carrier_species=("oxide", "reduced"))
    assert trace.carrier_closed and trace.temperature_closed and not trace.full_inventory_closed
    with pytest.raises(ThermochemicalCycleError) as error:
        engine.run(
            initial,
            (*stages[:2], reset),
            carrier_species=("oxide", "reduced"),
            require_full_inventory_closed=True,
        )
    assert error.value.trace.full_inventory_closed is False


def test_finite_overdraw_precedes_feeding_and_does_not_clip_inventory():
    engine, initial, stages = fixture()
    bad = replace(stages[0], pre_withdrawal_mol={"oxide": 1.1})
    with pytest.raises(ThermochemicalCycleError) as caught:
        engine.run(initial, (bad,), carrier_species=("oxide",))
    assert caught.value.before is initial and not caught.value.completed_steps
    assert caught.value.stage is bad and caught.value.__cause__ is not None
    too_much = replace(stages[0], conversions=(replace(stages[0].conversions[0], extent_mol=1.1),))
    with pytest.raises(ThermochemicalCycleError, match="finite"):
        engine.run(initial, (too_much,), carrier_species=("oxide",))


def test_second_stage_caloric_failure_keeps_prior_stage_and_partial_conversion():
    engine, initial, stages = fixture()
    bad = replace(stages[1], endpoint_temperature_k=1700.0)
    with pytest.raises(ThermochemicalCycleError) as error:
        engine.run(initial, (stages[0], bad), carrier_species=("oxide", "reduced"))
    assert len(error.value.completed_steps) == 1
    assert error.value.before is error.value.completed_steps[0].after
    assert error.value.stage is bad


@pytest.mark.parametrize(
    "kind",
    [
        "clock",
        "gap",
        "duplicate",
        "reference",
        "feed_reference",
        "feed_pressure",
        "foreign_species",
        "wrong_reaction",
    ],
)
def test_explicit_clock_reference_pressure_species_and_phase_contracts(kind):
    engine, initial, stages = fixture()
    if kind == "clock":
        stages = (stages[0], replace(stages[1], clock_id="other"))
    elif kind == "gap":
        stages = (stages[0], replace(stages[1], start_s=111.0))
    elif kind == "duplicate":
        stages = (stages[0], replace(stages[1], identifier=stages[0].identifier))
    elif kind == "reference":
        initial = replace(initial, energy_basis_id="other")
    elif kind in {"feed_reference", "feed_pressure"}:
        feed = stages[1].feeds[0]
        inventory = replace(
            feed.inventory,
            **({"energy_basis_id": "other"} if kind == "feed_reference" else {"pressure_pa": 2e5}),
        )
        stages = (stages[0], replace(stages[1], feeds=(replace(feed, inventory=inventory),)))
    elif kind == "foreign_species":
        initial = replace(initial, amounts_mol={"unknown": 1.0})
    elif kind == "wrong_reaction":
        command = stages[0].conversions[0]
        reaction = StoichiometricReaction(
            "reordered", command.reaction.species[::-1], command.reaction.coefficients[::-1]
        )
        stages = (replace(stages[0], conversions=(replace(command, reaction=reaction),)),)
    with pytest.raises(ValueError):
        engine.run(initial, stages, carrier_species=("oxide", "reduced"))


@pytest.mark.parametrize("value", [-1.0, float("nan"), True])
def test_invalid_amounts_and_empty_carrier_do_not_define_a_cycle(value):
    engine, initial, stages = fixture()
    with pytest.raises(ValueError):
        replace(initial, amounts_mol={"oxide": value})
    with pytest.raises(ValueError, match="nonempty"):
        engine.run(replace(initial, amounts_mol={}), stages, carrier_species=("oxide",))
