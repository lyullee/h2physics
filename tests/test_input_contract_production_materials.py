"""Family-specific invalid-input checks; no process/native solver is executed.

The cases exercise actual model input objects or their pre-calculation guards.
They do not establish equation accuracy, material calibration or native validity.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from h2physics.adapters.biological import Adm1Geometry
from h2physics.adapters.cantera_membrane import PorousTransportGeometry
from h2physics.adapters.cantera_multiphase import MultiphaseFeed
from h2physics.adapters.cantera_surface_reactor import CatalyticThermalBoundary
from h2physics.adapters.hydrogen_economics import AnnualFinancialBasis
from h2physics.adapters.microbial_cell import MicrobialCellStage
from h2physics.adapters.psa_cycle import PsaCycleEvidence
from h2physics.adapters.pv_electrolysis import PVStage
from h2physics.core import Origin
from h2physics.electrochemistry import HydrogenStack, StackGeometry
from h2physics.materials.elastic_cylinder import CylinderGeometry
from h2physics.materials.finite_volume import DiffusionDomain, DiffusionMesh
from h2physics.materials.transport import HydrogenCarrier, PowerLawSolubility, steady_permeation
from h2physics.observations import Variable
from h2physics.photochemistry import PhotonSupply
from h2physics.thermochemical import ThermochemicalInventory
from h2physics.uncertainty import JointParameterDomain

INPUT_FAMILY_IDS = (
    "production.electrolyzer", "production.fuel_cell", "production.photo",
    "production.thermochemical", "production.reforming", "production.gasification",
    "production.biological", "production.microbial_cell", "production.energy_coupling",
    "separation.psa", "separation.membrane", "materials.solubility",
    "materials.permeation", "materials.diffusion", "materials.integrity",
    "research.uncertainty", "research.economics",
)


def _forbidden_physics(*_args, **_kwargs):
    raise AssertionError("Malformed input reached the physics callback")


def _stack_input(**changes):
    args = dict(current_density_a_m2=10., temperature_k=300., mode="electrolysis")
    args.update(changes)
    model = HydrogenStack(StackGeometry(1, .01, .00201588), _forbidden_physics, {})
    return model.evaluate(**args)


def _construct(cls, baseline, changes):
    # Demonstrate an admissible parameter baseline, then change only the target.
    cls(**baseline)
    return cls(**(baseline | changes))


def _solubility_input(**changes):
    model = PowerLawSolubility(HydrogenCarrier("atomic_hydrogen", .00100794),
                              lambda _temperature: 1.e-6, .5)
    return model.concentration_mol_m3(**(dict(hydrogen_fugacity_pa=1.e5,
                                             temperature_k=300.) | changes))


def _permeation_input(**changes):
    model = PowerLawSolubility(HydrogenCarrier("atomic_hydrogen", .00100794),
                              _forbidden_physics, .5)
    return steady_permeation(model, **(dict(diffusivity_m2_s=1.e-10,
        thickness_m=.001, upstream_fugacity_pa=1.e5, downstream_fugacity_pa=0.,
        temperature_k=300.) | changes))


def _diffusion_input(**changes):
    owner = DiffusionDomain(HydrogenCarrier("atomic_hydrogen", .00100794),
                            DiffusionMesh.planar(.001, 3), _forbidden_physics)
    return owner.simulate(**(dict(time_s=(0., 1.), initial_mobile_mol_m3=(0., 0., 0.),
        boundary=_forbidden_physics, temperature_k=_forbidden_physics) | changes))


THERMAL = dict(evidence_id="authored-wall", wall_temperature_k=500., area_m2=1.,
               heat_transfer_w_m2_k=10., energy_residual_absolute_tolerance_j=.01)
BIO = dict(liquid_volume_m3=1., headspace_volume_m3=.1,
           gas_pipe_coefficient_m3_s_pa=1.e-8, external_pressure_pa=1.e5, temperature_k=300.)
MEC = dict(identifier="authored-stage", start_s=0., end_s=1., clock_id="authored-clock",
           anode_potential_v=-.2, electrolyte_potential_v=0.,
           cathode_potential_bracket_v=(-1., 0.),
           native_phase_mole_fractions={"gas": {"H2": 1.}}, evidence_id="authored", connected=True)
PV = dict(identifier="authored-stage", start_s=0., end_s=1., clock_id="authored-clock",
          effective_irradiance_w_m2=100., cell_temperature_k=300., stack_temperature_k=300.,
          source_id="authored-source", origin=Origin.SYNTHETIC)
PSA = dict(source_id="authored-source", energy_reference_id="authored-native-energy",
           gas_phase_scope_id="warm-gas", parameter_origin=Origin.SYNTHETIC)
PORES = dict(porosity=.3, tortuosity=2., mean_pore_radius_m=1.e-7, permeability_m2=1.e-14,
             thickness_m=.001, geometry_id="authored-pore", evidence_id="authored",
             origin=Origin.SYNTHETIC)
FINANCE = dict(currency="USD", base_year=2026, operating_year_label=2026,
    seconds_in_operating_year=31536000., annual_product_kg_at_gate=100.,
    annual_generated_h2_kg=100., annual_initial_h2_inventory_kg=0.,
    annual_final_h2_inventory_kg=0., annual_nonproduct_h2_out_kg=0.,
    product_grade_id="authored-grade", product_pressure_pa=1.e5,
    product_gate_evidence_id="authored-gate", representation="independent_annual_inputs",
    representation_evidence_id="authored-annual", annual_inventory_reconciliation_id="authored",
    annual_repetition_evidence_id="authored", capacity_factor=1.,
    capacity_factor_evidence_id="authored", unresolved_cost_resolutions={}, origin=Origin.SYNTHETIC)


@dataclass(frozen=True)
class InputCase:
    family: str
    scenario: str
    invoke: Callable
    message: str
    target: str


CASES = (
    InputCase("production.electrolyzer", "negative-current",
        lambda: _stack_input(current_density_a_m2=-1.), "nonnegative current",
        "HydrogenStack.evaluate"),
    InputCase("production.electrolyzer", "nonfinite-current",
        lambda: _stack_input(current_density_a_m2=float("nan")), "current density.*finite",
        "HydrogenStack.evaluate"),
    InputCase("production.fuel_cell", "zero-temperature",
        lambda: _stack_input(mode="fuel_cell", temperature_k=0.), "temperature.*positive",
        "HydrogenStack.evaluate"),
    InputCase("production.fuel_cell", "invalid-faradaic-efficiency",
        lambda: _stack_input(mode="fuel_cell", faradaic_efficiency=1.01), "Faradaic efficiency",
        "HydrogenStack.evaluate"),
    InputCase("production.photo", "negative-wavelength",
        lambda: PhotonSupply.from_lines([-400.e-9], [1.], geometry_id="beam", source_id="source"),
        "Wavelength|wavelength|Optical", "PhotonSupply.from_lines"),
    InputCase("production.photo", "negative-optical-power",
        lambda: PhotonSupply.from_lines([400.e-9], [-1.], geometry_id="beam", source_id="source"),
        "optical power", "PhotonSupply.from_lines"),
    InputCase("production.thermochemical", "negative-species-stock",
        lambda: ThermochemicalInventory({"H2": -1.}, 300., 1.e5, "basis"),
        "species amounts cannot be negative", "ThermochemicalInventory"),
    InputCase("production.thermochemical", "missing-energy-basis",
        lambda: ThermochemicalInventory({"H2": 1.}, 300., 1.e5, ""),
        "Declare", "ThermochemicalInventory"),
    InputCase("production.reforming", "negative-wall-area",
        lambda: _construct(CatalyticThermalBoundary, THERMAL, {"area_m2": -1.}),
        "area_m2.*positive", "CatalyticThermalBoundary"),
    InputCase("production.reforming", "nonfinite-wall-temperature",
        lambda: _construct(CatalyticThermalBoundary, THERMAL,
                           {"wall_temperature_k": float("nan")}),
        "wall_temperature_k.*finite", "CatalyticThermalBoundary"),
    InputCase("production.gasification", "zero-feed-pressure",
        lambda: MultiphaseFeed(500., 0., {"gas": {"H2": 1.}}, "source", Origin.SYNTHETIC),
        "feed absolute pressure.*positive", "MultiphaseFeed"),
    InputCase("production.gasification", "negative-feed-moles",
        lambda: MultiphaseFeed(500., 1.e5, {"gas": {"H2": -1.}}, "source", Origin.SYNTHETIC),
        "nonnegative", "MultiphaseFeed"),
    InputCase("production.biological", "zero-liquid-volume",
        lambda: _construct(Adm1Geometry, BIO, {"liquid_volume_m3": 0.}),
        "liquid_volume_m3.*positive", "Adm1Geometry"),
    InputCase("production.biological", "outside-biological-temperature-domain",
        lambda: _construct(Adm1Geometry, BIO, {"temperature_k": 400.}),
        "280", "Adm1Geometry"),
    InputCase("production.microbial_cell", "reversed-electrode-bracket",
        lambda: _construct(MicrobialCellStage, MEC, {"cathode_potential_bracket_v": (0., -1.)}),
        "increasing cathode", "MicrobialCellStage"),
    InputCase("production.microbial_cell", "unnormalized-native-composition",
        lambda: _construct(MicrobialCellStage, MEC,
                           {"native_phase_mole_fractions": {"gas": {"H2": .8}}}),
        "sum to one", "MicrobialCellStage"),
    InputCase("production.energy_coupling", "negative-irradiance",
        lambda: _construct(PVStage, PV, {"effective_irradiance_w_m2": -1.}),
        "Irradiance cannot be negative", "PVStage"),
    InputCase("production.energy_coupling", "reversed-source-clock",
        lambda: _construct(PVStage, PV, {"end_s": -1.}),
        "clock must increase", "PVStage"),
    InputCase("separation.psa", "negative-component-audit-budget",
        lambda: _construct(PsaCycleEvidence, PSA, {"component_absolute_tolerance_mol": -1.}),
        "component budget.*positive", "PsaCycleEvidence"),
    InputCase("separation.psa", "missing-native-energy-reference",
        lambda: _construct(PsaCycleEvidence, PSA, {"energy_reference_id": ""}),
        "native energy zero", "PsaCycleEvidence"),
    InputCase("separation.membrane", "impossible-porosity",
        lambda: _construct(PorousTransportGeometry, PORES, {"porosity": 1.1}),
        "Porosity", "PorousTransportGeometry"),
    InputCase("separation.membrane", "zero-membrane-thickness",
        lambda: _construct(PorousTransportGeometry, PORES, {"thickness_m": 0.}),
        "separation.*positive", "PorousTransportGeometry"),
    InputCase("materials.solubility", "negative-fugacity",
        lambda: _solubility_input(hydrogen_fugacity_pa=-1.), "Fugacity.*negative",
        "PowerLawSolubility.concentration_mol_m3"),
    InputCase("materials.solubility", "zero-temperature",
        lambda: _solubility_input(temperature_k=0.), "temperature.*positive",
        "PowerLawSolubility.concentration_mol_m3"),
    InputCase("materials.permeation", "negative-diffusivity",
        lambda: _permeation_input(diffusivity_m2_s=-1.e-10), "diffusivity.*positive",
        "steady_permeation"),
    InputCase("materials.permeation", "zero-wall-thickness",
        lambda: _permeation_input(thickness_m=0.), "thickness.*positive", "steady_permeation"),
    InputCase("materials.diffusion", "duplicate-output-time",
        lambda: _diffusion_input(time_s=(0., 0.)), "finite and increasing",
        "DiffusionDomain.simulate"),
    InputCase("materials.diffusion", "negative-initial-mobile-concentration",
        lambda: _diffusion_input(initial_mobile_mol_m3=(-1., 0., 0.)), "nonnegative",
        "DiffusionDomain.simulate"),
    InputCase("materials.integrity", "negative-inner-radius",
        lambda: CylinderGeometry(-.01, .02, "closed", "wall"), "inner radius.*positive",
        "CylinderGeometry"),
    InputCase("materials.integrity", "inverted-wall-radii",
        lambda: CylinderGeometry(.02, .01, "closed", "wall"), "Outer radius must exceed",
        "CylinderGeometry"),
    InputCase("research.uncertainty", "reversed-physical-domain",
        lambda: JointParameterDomain(Variable("p", "absolute_pressure", "Pa", "source"),
            "bounds", Origin.SYNTHETIC, 2.e5, 1.e5), "increasing.*bounds", "JointParameterDomain"),
    InputCase("research.uncertainty", "nonfinite-physical-domain",
        lambda: JointParameterDomain(Variable("p", "absolute_pressure", "Pa", "source"),
            "bounds", Origin.SYNTHETIC, 1.e5, float("inf")), "maximum.*finite",
        "JointParameterDomain"),
    InputCase("research.economics", "zero-annual-duration",
        lambda: _construct(AnnualFinancialBasis, FINANCE, {"seconds_in_operating_year": 0.}),
        "duration seconds.*positive", "AnnualFinancialBasis"),
    InputCase("research.economics", "nonfinite-product-pressure",
        lambda: _construct(AnnualFinancialBasis, FINANCE, {"product_pressure_pa": float("nan")}),
        "product pressure.*finite", "AnnualFinancialBasis"),
)


@pytest.mark.parametrize("case", CASES,
                         ids=lambda c: f"{c.family}::{c.scenario}")
def test_family_rejects_invalid_input(case, record_property):
    record_property("family", case.family)
    record_property("input_target", case.target)
    record_property("invalid_scenario", case.scenario)
    with pytest.raises(ValueError, match=case.message):
        case.invoke()
