"""Nominal known-answer checks of host formulae, not external-engine physics.

Synthetic coefficients define transparent numerical references. They are not
material parameters or production substitutes for the native property engines.
"""

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from h2physics.adapters.pv_electrolysis import PVBoundaryProfile, PVBoundarySample
from h2physics.core import Origin
from h2physics.electrochemistry import HydrogenStack, OhmicLoss, ReactionEnergy, StackGeometry
from h2physics.materials import (
    CylinderGeometry,
    CylinderPressureLoad,
    DiffusionDomain,
    DiffusionMesh,
    HydrogenCarrier,
    PowerLawSolubility,
    SurfaceCondition,
    TransportBoundary,
    lame_stress_field,
    steady_permeation,
)
from h2physics.observations import Variable
from h2physics.photochemistry import PhotonSupply
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
from h2physics.thermochemical import (
    FiniteThermochemicalCycle,
    PrescribedConversion,
    ThermochemicalEvidence,
    ThermochemicalInventory,
    ThermochemicalStage,
)
from h2physics.uncertainty import (
    IndependentParameterSpace,
    ParameterDistribution,
    UncertainModel,
    UncertaintyEvidence,
    independent_qmc_design,
    propagate,
)

FORMULA_FAMILY_IDS = (
    "production.electrolyzer", "production.fuel_cell", "production.photo",
    "production.thermochemical", "production.energy_coupling", "materials.solubility",
    "materials.permeation", "materials.diffusion", "materials.integrity",
    "research.uncertainty", "separation.membrane", "production.reforming",
    "production.microbial_cell", "production.gasification", "research.economics",
    "separation.psa", "production.biological",
)


def _stack(mode):
    stack = HydrogenStack(
        StackGeometry(5, .02, .00201588),
        lambda temperature: ReactionEnergy(200000., 240000., "authored-caloric", "liquid"),
        {"ohmic": OhmicLoss(lambda temperature: .001)},
    )
    actual = stack.evaluate(100., 300., mode=mode)
    # Exact defining constants, independently evaluated rather than importing F.
    faraday = 6.02214076e23 * 1.602176634e-19
    sign = 1. if mode == "electrolysis" else -1.
    voltage = 200000. / (2. * faraday) + sign * .1
    expected_rate = sign * 5. / faraday
    expected_electric = sign * 10. * voltage
    assert actual.current_a == pytest.approx(2.)
    assert actual.cell_voltage_v == pytest.approx(voltage, rel=2.e-14, abs=0.)
    assert actual.hydrogen_production_mol_s == pytest.approx(expected_rate, rel=2.e-14, abs=0.)
    assert actual.electric_input_w == pytest.approx(expected_electric, rel=2.e-14, abs=0.)
    assert actual.isothermal_heat_rejection_w == pytest.approx(
        expected_electric - expected_rate * 240000., rel=2.e-14, abs=0.)


def _photon_count():
    light = PhotonSupply.from_lines(
        (400.e-9, 600.e-9), (1., 2.), geometry_id="authored-beam", source_id="authored")
    # One watt divided by hc/lambda, then molecules-to-moles using N_A.
    conversion = 6.62607015e-34 * 299792458. * 6.02214076e23
    expected = (400.e-9 / conversion, 1200.e-9 / conversion)
    np.testing.assert_allclose(light.incident_photons_mol_s, expected, rtol=2.e-14)


def _thermal_conversion():
    species = (
        ChemicalSpecies("water", {"H": 2, "O": 1}, .018, "declared-water"),
        ChemicalSpecies("H2", {"H": 2}, .002, "declared-gas"),
        ChemicalSpecies("O2", {"O": 2}, .032, "declared-gas"),
    )
    caloric = FunctionalMolarEnthalpy(
        species, (lambda t, p: -240000. + 40. * (t - 300.),
                  lambda t, p: 30. * (t - 300.), lambda t, p: 20. * (t - 300.)),
        "authored-linear-molar-enthalpy", (290., 500.), (1.e4, 1.e6))
    model = FiniteThermochemicalCycle(caloric, ThermochemicalEvidence(
        "authored", "additive", "takeoff", "fixed-pressure", Origin.SYNTHETIC))
    reaction = StoichiometricReaction("authored-water", species, (-1., 1., .5))
    stage = ThermochemicalStage("warm-and-convert", 0., 10., "clock", 400.,
        (PrescribedConversion(reaction, .25, "authored-extent"),), "authored")
    actual = model.run(ThermochemicalInventory({"water": 2.}, 300., 1.e5, caloric.basis_id),
                       (stage,), carrier_species=("water",), require_carrier_closed=False,
                       require_temperature_closed=False)
    # Two mol water warmed by100K:8000J. Reaction at400K:60000J.
    assert actual.steps[0].conditioning_heat_required_j == pytest.approx(8000.)
    assert actual.steps[0].reaction_heat_required_j == pytest.approx(60000.)
    assert actual.net_heat_required_j == pytest.approx(68000.)
    assert actual.steps[0].mean_required_heat_w == pytest.approx(6800.)
    assert actual.final.amounts_mol == pytest.approx({"water": 1.75, "H2": .25, "O2": .125})


def _pv_profile_quadrature():
    profile = PVBoundaryProfile("authored-profile", "clock", Origin.SYNTHETIC, (
        PVBoundarySample(10., 200., 300., "left"),
        PVBoundarySample(16., 800., 330., "right")))
    stages = profile.stages(stack_temperature_k=310., maximum_gap_s=6., subdivisions_per_gap=3)
    assert [s.effective_irradiance_w_m2 for s in stages] == pytest.approx((300., 500., 700.))
    assert [s.cell_temperature_k for s in stages] == pytest.approx((305., 315., 325.))
    assert math.fsum((s.end_s - s.start_s) * s.effective_irradiance_w_m2
                     for s in stages) == pytest.approx(3000.)


def _solubility():
    law = PowerLawSolubility(HydrogenCarrier("atomic_hydrogen", .001), lambda t: 2.e-4, .5)
    assert law.concentration_mol_m3(90000., 300.) == pytest.approx(.06)


def _permeation():
    law = PowerLawSolubility(HydrogenCarrier("atomic_hydrogen", .001), lambda t: 2.e-4, .5)
    result = steady_permeation(law, diffusivity_m2_s=3.e-10, thickness_m=.002,
        upstream_fugacity_pa=90000., downstream_fugacity_pa=10000., temperature_k=300.)
    assert result.mobile_entity_flux_mol_m2_s == pytest.approx(6.e-9, rel=2.e-14, abs=0.)
    assert result.hydrogen_mass_flux_kg_m2_s == pytest.approx(6.e-12, rel=2.e-14, abs=0.)
    assert result.h2_equivalent_flux_mol_m2_s == pytest.approx(3.e-9, rel=2.e-14, abs=0.)


def _planar_diffusion():
    mesh = DiffusionMesh.planar(.01, 10, area_m2=.02)
    initial = 30. - 20. * mesh.cell_centers_m / .01
    model = DiffusionDomain(HydrogenCarrier("atomic_hydrogen", .001), mesh, lambda t: 1.e-5)
    trace = model.simulate((0., 2.), initial,
        boundary=lambda t: TransportBoundary(SurfaceCondition("concentration", 30.),
                                             SurfaceCondition("concentration", 10.)),
        temperature_k=lambda t: 300.)
    # Constant positive flow D*A*(30-10)/L=0.0004mol/s, integrated for2s.
    np.testing.assert_allclose(trace.mobile_mol_m3[-1], initial, rtol=0., atol=1.e-10)
    assert trace.left_integrated_mol[-1] == pytest.approx(.0008, rel=1.e-10, abs=0.)
    assert trace.right_integrated_mol[-1] == pytest.approx(.0008, rel=1.e-10, abs=0.)


def _lame_stress():
    result = lame_stress_field(CylinderGeometry(1., 2., "closed", "authored-cylinder"),
        CylinderPressureLoad(10., 2., "authored-pressure", Origin.SYNTHETIC), (1.5,),
        evidence_id="authored-analytic")
    assert result.radial_stress_pa[0] == pytest.approx(-110. / 27.)
    assert result.hoop_stress_pa[0] == pytest.approx(146. / 27.)
    assert result.axial_stress_pa[0] == pytest.approx(2. / 3.)
    assert result.von_mises_stress_pa[0] == pytest.approx(128. * math.sqrt(3.) / 27.)


def _ensemble_summary():
    space = IndependentParameterSpace((ParameterDistribution(
        Variable("x", "authored_coordinate", "1", "authored"), stats.uniform(1., 2.),
        "authored-uniform", "declared-bound", Origin.SYNTHETIC, 1., 3.),),
        "authored-independence", "authored-space")
    design = independent_qmc_design(space, power=4, seed=310)
    model = UncertainModel(lambda p: {"y": 3. * p["x"] + 2.},
        (Variable("y", "authored_response", "1"),), UncertaintyEvidence(
            "authored-linear", "v1", "stateless", "sample-moments-only", Origin.SYNTHETIC))
    result = propagate(design, model)
    summary = result.summarize((.5,))
    expected = [3. * float(row[0]) + 2. for row in design.values]
    mean = math.fsum(expected) / 16.
    variance = math.fsum((v - mean) ** 2 for v in expected) / 16.
    ordered = sorted(expected)
    assert summary.mean[0] == pytest.approx(mean, rel=2.e-14, abs=0.)
    assert summary.population_variance[0] == pytest.approx(variance, rel=2.e-14, abs=0.)
    assert summary.quantiles[0, 0] == pytest.approx((ordered[7] + ordered[8]) / 2.)


def _membrane_unit_conversion():
    """Only host unit conversion is asserted, not the native flux equation."""
    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_membrane import (
        CanteraDustyGasTransport,
        MembraneEndpoint,
        MembraneTransportEvidence,
        PorousTransportGeometry,
    )

    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    names = ("H2", "N2", "AR")

    def phase_factory():
        species = {s.name: s for s in ct.Species.list_from_yaml(raw.decode(), section="species")}
        return ct.Solution(thermo="ideal-gas", species=[species[name] for name in names],
                           transport_model="multicomponent")

    basis = MechanismBasis("installed-H2-N2-Ar-host-units", hashlib.sha256(raw).hexdigest(),
        "installed-Cantera-BSD-3-Clause", ("https://cantera.org/3.2/python/transport.html",),
        300., 1000., .001, 2.e5)
    evidence = MembraneTransportEvidence("installed-transport", "warm-gas", "ideal-gas",
                                         "native-reference", "H2-spin-unresolved")
    model = CanteraDustyGasTransport(phase_factory, basis, evidence=evidence)
    pore = PorousTransportGeometry(.35, 2.5, 50.e-9, 0., .001,
        "authored-geometry", "authored", Origin.SYNTHETIC)

    def endpoint(side, fractions):
        return MembraneEndpoint(330., 101325., names, fractions, "mole", side,
            "warm-gas", "authored-geometry", "authored", Origin.SYNTHETIC)

    result = model.flux(endpoint("left", (.7, .2, .1)), endpoint("right", (.4, .5, .1)), pore)
    for index, molecular_weight in enumerate(result.molecular_weights_kg_mol):
        expected_mol = float(result.native_flux_kmol_m2_s[index]) * 1000.
        assert result.molar_flux_mol_m2_s[index] == pytest.approx(expected_mol, rel=2.e-14, abs=0.)
        assert result.mass_flux_kg_m2_s[index] == pytest.approx(
            expected_mol * float(molecular_weight), rel=2.e-14, abs=0.)
    assert any(abs(v) > 1.e-6 for v in result.molar_flux_mol_m2_s)


def _catalytic_energy_accounting():
    """Use actual native properties as inputs to host amount/energy arithmetic."""
    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis, NativeMechanismSource, ReactiveState
    from h2physics.adapters.cantera_surface_reactor import CanteraCatalyticSurfaceReactor

    path = next(Path(directory) / "ptcombust.yaml" for directory in ct.get_data_directories()
                if (Path(directory) / "ptcombust.yaml").is_file())
    raw = path.read_bytes()
    basis = MechanismBasis("installed-catalyst-host-accounting", hashlib.sha256(raw).hexdigest(),
        "installed-mechanism-separate-rights", ("https://cantera.org/3.2/",),
        600., 1400., 1.e4, 1.e6)
    owner = CanteraCatalyticSurfaceReactor(NativeMechanismSource(raw, "gas"), basis,
        surface_phase_name="Pt_surf", gas_phase_name="gas")
    native = ct.Interface(yaml=raw.decode(), name="Pt_surf")
    coverage = {name: float(name == "PT(S)") for name in native.species_names}
    trace = owner.run(ReactiveState(900., 101325., {"H2": .1, "O2": .05, "AR": .85}),
        (0., 1.e-6), initial_coverages=coverage, surface_area_m2=.001, gas_volume_m3=1.e-4,
        clock_id="authored", evidence_id="host-energy-only", maximum_time_step_s=1.e-7,
        relative_tolerance=1.e-9, absolute_tolerance=1.e-15,
        element_absolute_tolerance_mol=1.e-9, site_fraction_tolerance=1.e-8,
        minimum_gas_mass_kg=1.e-12)
    surface = trace.native_interface
    reactor = trace.native_reactor
    point = trace.points[-1]
    surface_energy = math.fsum(float(n) * float(h) / 1000.
        for n, h in zip(point.surface_species_mol, surface.partial_molar_enthalpies, strict=True))
    expected = float(reactor.mass) * float(trace.native_gas.int_energy_mass) + surface_energy
    assert abs(surface_energy) > 1.e-10
    assert point.combined_internal_energy_j == pytest.approx(expected, rel=2.e-13, abs=1.e-12)


def _microbial_charge_stoichiometry():
    from examples.microbial_cell import build_problem

    model, initial, stages = build_problem()
    trace = model.run(initial, stages[:1])
    faraday = 6.02214076e23 * 1.602176634e-19
    step = trace.steps[0]
    expected_hydrogen = step.current_a * (step.stage.end_s - step.stage.start_s) / (2. * faraday)
    assert expected_hydrogen > 0.
    assert step.hydrogen_generated_mol == pytest.approx(expected_hydrogen, rel=1.e-8, abs=0.)
    assert trace.transferred_electrons_mol == pytest.approx(2. * expected_hydrogen, rel=1.e-8, abs=0.)


def _gasification_mass_projection():
    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_multiphase import (
        CanteraMultiphaseEquilibrium,
        EquilibriumPhase,
        MultiphaseFeed,
    )
    phases = []
    for file, name, role, identifier in (
        ("gri30.yaml", "gri30", "gas", "gas"),
        ("graphite.yaml", "graphite", "solid", "carbon"),
    ):
        raw = (Path(ct.__file__).parent / "data" / file).read_bytes()
        def factory(raw=raw, name=name):
            return ct.Solution(yaml=raw.decode(), name=name)
        basis = MechanismBasis("installed-" + name, hashlib.sha256(raw).hexdigest(),
            "installed-mechanism-separate-rights", ("https://cantera.org/3.2/",),
            300., 2800., 1.e4, 1.e6)
        phases.append(EquilibriumPhase(identifier, role, factory, basis,
            "native-NASA-reference", "native-spin-unresolved"))
    result = CanteraMultiphaseEquilibrium(phases).equilibrate(MultiphaseFeed(
        750., 101325., {"gas": {"CH4": .6, "H2O": .12, "CO2": .08, "AR": .2},
        "carbon": {"C(gr)": 0.}}, "authored-finite-feed", Origin.SYNTHETIC))
    molecular_weights = {(spec.phase_id, name): float(weight) / 1000.
        for spec, native in zip(phases, result.owned_phases, strict=True)
        for name, weight in zip(native.species_names, native.molecular_weights, strict=True)}
    expected = math.fsum(float(amount) * molecular_weights[key]
        for key, amount in zip(result.species_keys, result.final.species_mol, strict=True))
    assert expected > 0.
    assert result.final.mass_kg == pytest.approx(expected, rel=2.e-13, abs=0.)


def _utility_cost_arithmetic():
    from h2physics.adapters.physical_economics import (
        PhysicalCostProjection,
        QuantityBoundary,
        ReportingWindow,
        SourceSnapshot,
        UtilityTariff,
    )
    # This is an explicit caller-owned synthetic input ledger, not a native result.
    source = (1200., 700., .01)
    window = ReportingWindow(0., 10., "authored-ledger-clock", "original-input-ledger",
        "generated_h2_kg")
    class LedgerAdapter:
        identifier = "original-synthetic-input-ledger"
        def snapshot(self, source, window, hydrogen_id):
            quantities = dict(zip(("electrical_work_into_j", "required_heat_input_j", "generated_h2_kg"), source))
            boundaries = {name: QuantityBoundary(name, name + "-boundary", "authored",
                "synthetic-input", (name,) if name.endswith("_j") else ()) for name in quantities}
            return SourceSnapshot(source, window, hydrogen_id, self.identifier,
                "declared-synthetic-input", quantities, boundaries, (), source, (source,))
    projection = PhysicalCostProjection.from_source(source, LedgerAdapter(), window, hydrogen_id="H2")
    quotes = tuple(UtilityTariff(name, rate, "USD", 2020, "authored-quote", name + "-boundary",
        Origin.SYNTHETIC) for name, rate in (("electrical_work_into_j", .002), ("required_heat_input_j", .003)))
    cost = projection.price_window(quotes)
    assert [row[2] for row in cost.line_items] == pytest.approx([2.4, 2.1])
    assert cost.total_usd == pytest.approx(4.5)


def _psa_ratio_accounting():
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    if not (root / "artifacts/native_packages/psa_dynamic/runner.py").is_file():
        raise RuntimeError("Pinned actual PSA provider unavailable")
    spec = importlib.util.spec_from_file_location("authored_psa_inputs", root / "tests/test_psa_cycle.py")
    inputs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inputs)
    trace = inputs.adapter().run(start_time_s=100., clock_id="authored-formula-clock")
    point = trace.points[-1]
    assert point.product_mol[0] > 0.
    assert trace.totals.hydrogen_product_purity == pytest.approx(
        float(point.product_mol[0]) / math.fsum(point.product_mol), rel=2.e-13, abs=0.)
    assert trace.totals.hydrogen_product_to_feed_ratio == pytest.approx(
        float(point.product_mol[0]) / float(point.feed_mol[0]), rel=2.e-13, abs=0.)


def _biological_amount_conversion():
    import sys
    root = Path(__file__).resolve().parents[1]
    for directory in reversed(("native_biological_core_fixed", "native_biological_packages")):
        selected = str(root / "artifacts" / directory)
        if selected not in sys.path:
            sys.path.insert(0, selected)
    from h2physics.adapters.biological import QsdSanNative
    from scripts.check_biological import make_case
    reactor = make_case(QsdSanNative.from_installed())
    trace = reactor.run(start_time_s=864000., end_time_s=864001., sample_count=3, max_step_s=1.)
    point = trace.points[0]
    # Declared gas concentration is mol/m3, original geometry is .005m3.
    # Native molecular weights use kg/kmol; the declared concentration uses mol/m3.
    mass_per_mol = float(reactor.native_components.chem_MW[reactor._ids.index("S_h2")]) / 1000.
    expected = .005 * 1.e-6 * mass_per_mol
    assert expected > 0.
    assert point.headspace_hydrogen_kg == pytest.approx(expected, rel=2.e-13, abs=0.)


@dataclass(frozen=True)
class FormulaCase:
    family: str
    target: str
    oracle: str
    check: object
    scope_kind: str = "model_equation"


CASES = (
    FormulaCase("production.electrolyzer", "HydrogenStack.evaluate",
        "Independent Faraday/current/voltage/power arithmetic with exact defining constants",
        lambda: _stack("electrolysis")),
    FormulaCase("production.fuel_cell", "HydrogenStack.evaluate",
        "Independent signed Faraday and electric-minus-reaction-enthalpy arithmetic",
        lambda: _stack("fuel_cell")),
    FormulaCase("production.photo", "PhotonSupply.from_lines",
        "Power divided by hc/lambda and Avogadro constant", _photon_count),
    FormulaCase("production.thermochemical", "FiniteThermochemicalCycle.run",
        "8000J sensible plus60000J reaction heat, finite stoichiometric amounts", _thermal_conversion),
    FormulaCase("production.energy_coupling", "PVBoundaryProfile.stages",
        "Nominal linear profile midpoint integration3000J/m2; not PV native IV physics",
        _pv_profile_quadrature, "supporting_geometry_or_accounting"),
    FormulaCase("materials.solubility", "PowerLawSolubility.concentration_mol_m3",
        "K*sqrt(f)=0.0002*300=0.06mol/m3", _solubility),
    FormulaCase("materials.permeation", "steady_permeation",
        "D*(c_up-c_down)/L and independent atomic-H mass/H2 conversions", _permeation),
    FormulaCase("materials.diffusion", "DiffusionDomain.simulate",
        "Linear Fick profile and nonzero extensive throughflow0.0008mol over2s", _planar_diffusion),
    FormulaCase("materials.integrity", "lame_stress_field",
        "Exact rational Lame stress components and vonMises at r=1.5", _lame_stress),
    FormulaCase("research.uncertainty", "PropagationResult.summarize",
        "Independent fsum population moments/median of16 actual model cases; not sampler validation",
        _ensemble_summary, "supporting_geometry_or_accounting"),
    FormulaCase("separation.membrane", "CanteraDustyGasTransport.flux host unit projection",
        "Native nonzero kmol flux times1000 and species kg/mol; no native transport oracle",
        _membrane_unit_conversion, "supporting_geometry_or_accounting"),
    FormulaCase("production.reforming", "CatalyticSurfacePoint combined energy projection",
        "Actual native surface partial enthalpies times mol/1000 plus gas mass*u; no kinetic oracle",
        _catalytic_energy_accounting, "supporting_geometry_or_accounting"),
    FormulaCase("production.microbial_cell", "FiniteMicrobialCell.run Faraday material accounting",
        "Actual native cathode current times seconds/(2*exact Faraday), one nominal finite stage",
        _microbial_charge_stoichiometry),
    FormulaCase("production.gasification", "MultiphaseSnapshot mass projection",
        "Actual native species mol times independent native kg/mol factors and fsum; no equilibrium oracle",
        _gasification_mass_projection, "supporting_geometry_or_accounting"),
    FormulaCase("research.economics", "PhysicalCostProjection.price_window",
        "Explicit synthetic caller ledger:1200J*.002USD/J+700J*.003USD/J=4.5USD",
        _utility_cost_arithmetic, "supporting_geometry_or_accounting"),
    FormulaCase("separation.psa", "PsaCycleTotals purity and product/feed arithmetic",
        "Actual native finite-cycle component ledger ratios, not adsorption/PDE validation",
        _psa_ratio_accounting, "supporting_geometry_or_accounting"),
    FormulaCase("production.biological", "BiologicalPoint headspace hydrogen conversion",
        "Positive declared mol/m3 times .005m3 times actual species kg/mol; no ADM1 kinetic oracle",
        _biological_amount_conversion, "supporting_geometry_or_accounting"),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.family)
def test_host_formula_known_answer(case, record_property):
    record_property("family", case.family)
    record_property("formula_target", case.target)
    record_property("oracle_description", case.oracle)
    record_property("scope_kind", case.scope_kind)
    case.check()
