"""Restricted material closure, native owner and finite reactor handoff."""
import numpy as np
import pytest

from h2physics.core import Origin
from h2physics.reactions import conversion_heat_j
from h2physics.storage.redox_equilibrium import SolidDensityEvidence, iron_oxide_steam_redox
from h2physics.storage.solid_reaction import (
    FiniteSolidReactionReactor,
    SolidReactionEvidence,
    SolidReactionStep,
)
from h2physics.thermochemical import ThermochemicalInventory

ct = pytest.importorskip("cantera")


@pytest.fixture
def closure():
    def density(value):
        return SolidDensityEvidence(value, "authored-constant-volume-fixture", Origin.SYNTHETIC,
                                    "synthetic density for software integration, not material measurement")
    return iron_oxide_steam_redox(ferrous_density=density(5700), magnetite_density=density(5200))


def solve(model, *, hydrogen=.01, scale=1., temperature=1000):
    return model.equilibrate({key: scale*value for key,value in {
        "FeO": 3., "H2O": 1., "Fe3O4": 1., "H2": hydrogen}.items()},
        temperature_k=temperature, pressure_pa=101325, source_id="authored-feed", origin=Origin.SYNTHETIC)


def test_native_material_prediction_selects_forward_and_reverse_without_supplied_extent(closure):
    forward = solve(closure)
    reverse = solve(closure, hydrogen=.2)
    assert forward.conversion.extent_mol > 0
    assert reverse.conversion.extent_mol < 0
    def ratio(result):
        return result.conversion.final_amounts["H2"]/result.conversion.final_amounts["H2O"]
    assert ratio(forward) == pytest.approx(ratio(reverse), rel=1e-8)
    for result in (forward,reverse):
        assert result.native_result.accepted
        assert isinstance(result.native_result.native_mixture,ct.Mixture)
        assert result.maximum_stoichiometry_residual_mol < 1e-10
        assert abs(result.conversion.mass_residual_kg) < 1e-12
        caloric_heat = conversion_heat_j(result.conversion,closure.caloric,
            inlet_temperature_k=1000,outlet_temperature_k=1000,pressure_pa=101325)
        assert result.heat_into_j == pytest.approx(caloric_heat,abs=1e-7)


def test_temperature_changes_predicted_equilibrium_and_finite_amounts_scale(closure):
    original = solve(closure)
    scaled = solve(closure,scale=7.)
    hot = solve(closure,temperature=1400)
    assert scaled.conversion.extent_mol == pytest.approx(7*original.conversion.extent_mol,rel=1e-8)
    assert scaled.heat_into_j == pytest.approx(7*original.heat_into_j,rel=1e-8)
    assert hot.conversion.extent_mol != pytest.approx(original.conversion.extent_mol,rel=.01)


def test_equilibrium_driven_rate_reaches_existing_finite_reactor_and_energy_balance(closure):
    equilibrium = solve(closure,temperature=1100)
    kinetics = closure.relaxation_kinetics(.2,identifier="authored-relaxation",
        source_id="synthetic-k-0.2-per-second",origin=Origin.SYNTHETIC)
    inventory = ThermochemicalInventory(dict(zip((s.identifier for s in closure.reaction.species),
                            equilibrium.conversion.initial_mol,strict=True)),
        1100,101325,closure.basis_id)
    expected = closure.reaction.convert(inventory.amounts_mol,.2*equilibrium.conversion.extent_mol)
    heat = conversion_heat_j(expected,closure.caloric,inlet_temperature_k=1100,
                             outlet_temperature_k=1100,pressure_pa=101325)
    evidence = SolidReactionEvidence("restricted-oxide-reaction",closure.source_id,
        closure.basis_id,"common-temperature","held-pressure","no-takeoff",Origin.SYNTHETIC)
    reactor = FiniteSolidReactionReactor(closure.caloric,kinetics,evidence,
        hydrogen_species="H2",water_species="H2O",mode="hydrolysis")
    trace = reactor.run(inventory,(SolidReactionStep("one",0,1,"test-seconds",heat,
                                                   (900,1500),"authored-step"),))
    assert trace.hydrogen_generated_mol == pytest.approx(expected.extent_mol,rel=1e-8)
    assert trace.final.temperature_k == pytest.approx(1100,abs=1e-5)
    assert np.max(abs(trace.element_residual_mol)) < 1e-10
    assert abs(trace.enthalpy_residual_j) < 1e-5


def test_restricted_material_temperature_and_unknown_inventory_refused(closure):
    with pytest.raises(ValueError):
        solve(closure,temperature=800)
    with pytest.raises(ValueError,match="undeclared"):
        closure.equilibrate({"CO":1},temperature_k=1000,pressure_pa=101325,source_id="wrong-material")
    with pytest.raises(ValueError,match="negative"):
        closure.relaxation_kinetics(-.1,identifier="invalid",source_id="test",origin=Origin.SYNTHETIC)


def test_pure_solid_seal_ignores_redundant_serialization_but_detects_physical_changes(closure):
    from h2physics.adapters.cantera_volume import _phase_fingerprint
    phase = closure.phases[2].factory()
    before = _phase_fingerprint(phase,include_reactions=True)
    ct.Mixture([(phase,1.)])
    assert _phase_fingerprint(phase,include_reactions=True) == before
    definition = dict(phase.species(0).input_data)
    definition["equation-of-state"]={"model":"constant-volume","density":5300.}
    changed = ct.Solution(name="different-density",thermo="fixed-stoichiometry",
                          species=[ct.Species.from_dict(definition)])
    changed.TP=1000,101325
    assert _phase_fingerprint(changed,include_reactions=True) != before
    species = phase.species(0)
    thermo = species.thermo
    coefficients = thermo.coeffs.copy()
    coefficients[7] += 1.
    coefficients[-1] += 1.
    species.thermo = type(thermo)(thermo.min_temp,thermo.max_temp,thermo.reference_pressure,coefficients)
    phase.modify_species(0,species)
    assert _phase_fingerprint(phase,include_reactions=True) != before
