"""Actual producer-to-consumer contracts, excluding native engine physics accuracy."""

import math
from dataclasses import dataclass, replace

import numpy as np
import pytest

from h2physics.core import Origin


def _existing(module, entry, **kwargs):
    import importlib
    outcome = getattr(importlib.import_module('validation.cases.' + module), entry)(
        work_directory=None, **kwargs)
    assert outcome.accepted and outcome.metrics


def _pv_charge():
    _existing('electrolysis_linepack', 'validate_charge',
              native_packages='artifacts/native_pvlib_packages', native_linepack=True)


def _fuel_cell():
    _existing('cantera_fuel_cell_coupled', 'validate_contract')


def _photo():
    _existing('photochemistry', 'validate_adjacent_finite_operation')


def _membrane_heat():
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_membrane import (
        CanteraDustyGasTransport,
        MembraneEndpoint,
        MembraneTransportEvidence,
        PorousTransportGeometry,
    )
    from h2physics.adapters.cantera_membrane_device import (
        CanteraFiniteMembraneDevice,
        FiniteMembraneParameters,
        MembraneIntegrationSettings,
    )
    from h2physics.adapters.cantera_membrane_heat import bind_cantera_membrane_thermostat_heat
    from h2physics.adapters.thermal_utilities import HeatWindow

    raw = (Path(ct.__file__).parent/'data/h2o2.yaml').read_bytes()
    names = ('H2','N2','AR')
    found = {sp.name:sp for sp in ct.Species.list_from_yaml(raw.decode(),section='species')}
    def factory():
        return ct.Solution(thermo='ideal-gas',species=[found[n] for n in names],
                           transport_model='multicomponent')
    basis = MechanismBasis('installed-frozen-native',hashlib.sha256(raw).hexdigest(),
        'Cantera-BSD-3-Clause',('https://cantera.org/3.2/',),300.,1000.,1e4,2e6)
    geometry = PorousTransportGeometry(.35,2.,1e-7,1e-12,1e-3,'geometry','authored',Origin.SYNTHETIC)
    evidence = MembraneTransportEvidence('native','warm','frozen-neutral','native-reference','unresolved-spin')
    def endpoint(side,pressure,fractions):
        return MembraneEndpoint(330.,pressure,names,fractions,'mole',side,'warm',
                                'geometry','authored',Origin.SYNTHETIC)
    owner = CanteraFiniteMembraneDevice(CanteraDustyGasTransport(factory,basis,evidence=evidence))
    parameters = FiniteMembraneParameters(.01,.01,.001,'physical-seconds',0.,.22,
        'imposed-thermostats','authored',Origin.SYNTHETIC)
    trace = owner.run(endpoint('left',2e5,(.7,.2,.1)),endpoint('right',1e5,(.3,.6,.1)),
        geometry,parameters,(0.,.1,.2),settings=MembraneIntegrationSettings(maximum_time_step_s=.02))
    duties = bind_cantera_membrane_thermostat_heat(trace,HeatWindow(0.,.2,'physical-seconds','authored'))
    assert len(duties)==2
    for side,duty in enumerate(duties):
        duty.require_current()
        assert duty.snapshot.source is trace
        np.testing.assert_array_equal(duty.snapshot.heat_into_process_j,np.diff(trace.thermostat_heat_j[:,side]))
    with pytest.raises(ValueError):
        bind_cantera_membrane_thermostat_heat(trace,HeatWindow(0.,.2,'foreign','negative'))


def _catalytic_heat():
    _existing('cantera_surface_reactor', 'validate_wall_heat_handoff')


def _material_source():
    from h2physics.adapters.diffusion_finite_source import source_from_diffusion_result
    from h2physics.materials import (
        DiffusionSlab,
        HydrogenCarrier,
        PowerLawSolubility,
        steady_permeation,
    )
    from h2physics.materials.transport import SlabBoundary, SurfaceCondition
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    gas = CoolPropProperties('Hydrogen')
    state = gas.state_pt(101325., 300.)
    carrier = HydrogenCarrier('molecular_hydrogen', gas.molar_mass_kg_mol)
    law = PowerLawSolubility(carrier, lambda t: .01, .5)
    rate = steady_permeation(law, diffusivity_m2_s=1e-9, thickness_m=.01,
        upstream_fugacity_pa=1e6, downstream_fugacity_pa=1e5, temperature_k=300.)
    assert rate.mobile_entity_flux_mol_m2_s > 0.
    diffusion = DiffusionSlab(carrier, thickness_m=.01, cells=5,
        diffusivity_m2_s=lambda t: 1e-9).simulate([0., 1., 2.], np.full(5, 100.),
        boundary=lambda t: SlabBoundary(SurfaceCondition('flux', 0.),
            SurfaceCondition('flux', rate.mobile_entity_flux_mol_m2_s)),
        temperature_k=lambda t: 300.)
    location = SourceLocation('solid-exit', 'clock', 'xyz', (0., 0., 0.), (1., 0., 0.))
    args = dict(surface_area_m2=.25, location=location,
        clock_alignment_evidence_id='same-physical-seconds',
        state_projection_evidence_id='explicit-CoolProp-carrier-state',
        source_evidence_id='actual-diffusion-outward-flux', gas_state=state,
        origin=Origin.PREDICTED)
    linked = source_from_diffusion_result(diffusion, **args).require_current()
    expected = np.diff(diffusion.right_integrated_flux_mol_m2)*.25*carrier.molar_mass_kg_mol
    np.testing.assert_allclose(linked.source.mass_kg, expected, rtol=1e-13, atol=0.)
    assert np.array_equal(linked.source.edges_s, diffusion.time_s)
    assert linked.source.state.basis == state.basis
    for bad_state in (CoolPropProperties('Nitrogen').state_pt(101325., 300.),
                      gas.saturated(101325.,0.)):
        with pytest.raises(ValueError):
            source_from_diffusion_result(diffusion, **{**args, 'gas_state': bad_state})


def _diffusion_stress():
    from h2physics.materials import (
        CylinderGeometry,
        CylinderPressureLoad,
        DiffusionDomain,
        DiffusionMesh,
        HydrogenCarrier,
        HydrogenConcentrationEigenstrainProfile,
        IsotropicThermoelasticMaterial,
        RadialTemperatureProfile,
        SurfaceCondition,
        TransportBoundary,
        radial_hydrogen_eigenstrain_cylinder,
    )
    carrier = HydrogenCarrier('atomic_hydrogen', .001008)
    mesh = DiffusionMesh.planar(.01, 8, area_m2=.02)
    diffusion = DiffusionDomain(carrier, mesh, lambda t: 1e-8).simulate(
        (0., 100.), np.linspace(20., 10., 8),
        boundary=lambda t: TransportBoundary(SurfaceCondition('concentration', 20.),
                                              SurfaceCondition('concentration', 10.)),
        temperature_k=lambda t: 300.)
    # Explicit one-way caller mapping of planar depth to cylindrical radius;
    # append the exact imposed boundary values, not invented solver samples.
    radii = np.r_[.05, .05 + mesh.cell_centers_m, .06]
    values = np.r_[20., diffusion.mobile_mol_m3[-1], 10.]
    profile = HydrogenConcentrationEigenstrainProfile(carrier, 'mobile-mol/m3',
        radii, values, 0., 1e-6, 300., 'actual-diffusion-profile', 'declared-depth-to-radius')
    temperature = RadialTemperatureProfile(radii, np.full(len(radii), 300.), 300., 'constant', 'authored')
    geometry = CylinderGeometry(.05, .06, 'closed', 'authored')
    load = CylinderPressureLoad(1e5, 1e5, 'equal-pressure', Origin.SYNTHETIC)
    material = IsotropicThermoelasticMaterial(190e9, .29, 12e-6, 'authored', 'authored')
    result = radial_hydrogen_eigenstrain_cylinder(geometry, load, temperature,
        material, profile, radii, axial_restraint='free', evidence_id='one-way-isotropic')
    result.require_current()
    assert result.hydrogen_profile is profile
    assert np.array_equal(profile.concentration_mol_m3[1:-1], diffusion.mobile_mol_m3[-1])
    assert np.max(abs(result.hydrogen_hoop_stress_pa)) > 0.
    with pytest.raises(ValueError, match='temperature reference'):
        radial_hydrogen_eigenstrain_cylinder(geometry, load, temperature, material,
            replace(profile, reference_temperature_k=301.), radii,
            axial_restraint='free', evidence_id='wrong-reference')


def _mec_cost():
    from examples.microbial_economics import problem
    from h2physics.adapters.microbial_economics import MicrobialCostProjection
    from h2physics.adapters.physical_economics import ReportingWindow
    projection, _, _, cost = problem()
    projection.require_current()
    trace = projection.source
    assert trace.require_current() is trace
    assert projection.quantities['generated_h2_kg'] > 0.
    assert cost.total_usd > 0. and math.isfinite(cost.total_usd)
    with pytest.raises(ValueError):
        MicrobialCostProjection.from_microbial_cell(trace,
            ReportingWindow(trace.steps[0].stage.start_s, trace.steps[-1].stage.end_s,
                            'wrong-clock', 'wrong-clock', 'generated_h2_kg'),
            hydrogen_id='hydrogen')


def _psa_audit():
    import test_psa_cycle as inputs

    from h2physics.adapters.adsorption_cycle_operation import audit_adsorption_cycle
    run = inputs.adapter().run(start_time_s=100., clock_id='physical-seconds')
    args = dict(clock_id=run.clock_id, period_s=run.native_schedule['cycle_time_s'],
        native_geometry_evidence_id='actual-native-cell-geometry',
        component_tolerance_mol=1e-7, energy_tolerance_j=1e-4)
    operation = audit_adsorption_cycle(run, **args)
    assert operation.run is run
    assert len(operation.checkpoints) == len(run.points)
    assert operation.checkpoints[-1].native_point is run.points[-1]
    with pytest.raises(ValueError, match='clock'):
        audit_adsorption_cycle(run, **{**args, 'clock_id': 'foreign-clock'})


def _thermochemical_solid():
    from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
    from h2physics.storage.solid_reaction import (
        FiniteSolidReactionReactor,
        SolidReactionEvidence,
        SolidReactionKinetics,
        SolidReactionStep,
    )
    from h2physics.thermochemical import (
        FiniteThermochemicalCycle,
        PrescribedConversion,
        ThermochemicalEvidence,
        ThermochemicalInventory,
        ThermochemicalStage,
    )
    species = (ChemicalSpecies('rich', {'Al': 1, 'H': 2}, .029, 'solid'),
        ChemicalSpecies('spent', {'Al': 1}, .027, 'solid'),
        ChemicalSpecies('H2', {'H': 2}, .002, 'gas'))
    provider = FunctionalMolarEnthalpy(species,
        tuple(lambda t,p,cp=cp:cp*(t-300.) for cp in (30.,18.,12.)),
        'authored-common', (200.,900.), (1e4,1e6))
    reaction = StoichiometricReaction('declared', species, (-1.,1.,1.))
    first = FiniteThermochemicalCycle(provider, ThermochemicalEvidence(
        'first','additive','none','fixed-P',Origin.SYNTHETIC)).run(
        ThermochemicalInventory({'rich':2.},300.,1e5,provider.basis_id),
        (ThermochemicalStage('first',0.,1.,'clock',300.,
            (PrescribedConversion(reaction,.2,'authored'),),'authored'),),
        carrier_species=('rich',),require_carrier_closed=False,require_temperature_closed=False)
    kinetics = SolidReactionKinetics(reaction,lambda state,pars:.1,
        'fixed-rate','authored',Origin.SYNTHETIC,{})
    evidence = SolidReactionEvidence('second','balanced',provider.basis_id,
        'same-T','fixed-P','none',Origin.SYNTHETIC)
    reactor = FiniteSolidReactionReactor(provider,kinetics,evidence,hydrogen_species='H2',mode='decomposition')
    second = reactor.run(first.final,(SolidReactionStep('second',1.,2.,'clock',0.,(200.,900.),'authored'),))
    assert dict(second.initial.amounts_mol) == dict(first.final.amounts_mol)
    assert second.initial.energy_basis_id == first.final.energy_basis_id
    assert second.final.amounts_mol['rich'] == pytest.approx(1.7)
    assert second.final.amounts_mol['H2'] == pytest.approx(.3)
    with pytest.raises(ValueError):
        reactor.run(replace(first.final,energy_basis_id='foreign'),
            (SolidReactionStep('second',1.,2.,'clock',0.,(200.,900.),'authored'),))


def _stack_uncertainty():
    from scipy import stats

    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry
    from h2physics.observations import Variable
    from h2physics.uncertainty import (
        IndependentParameterSpace,
        ParameterDistribution,
        UncertainModel,
        UncertaintyEvidence,
        independent_qmc_design,
        propagate,
    )
    stack = HydrogenStack(StackGeometry(5,.02,.00201588),
        lambda t:ReactionEnergy(200000.,240000.,'authored','liquid'),{})
    space = IndependentParameterSpace((ParameterDistribution(
        Variable('j','current_density','A/m2','declared'),stats.uniform(10.,20.),
        'uniform','authored',Origin.SYNTHETIC,10.,30.),),'independent','stack-inputs')
    seen=[]
    def physical(parameters):
        result=stack.evaluate(parameters['j'],300.,mode='electrolysis')
        seen.append(result)
        return {'h2':result.hydrogen_production_mol_s}
    owner=UncertainModel(physical,(Variable('h2','molar_flow','mol/s','H2'),),
        UncertaintyEvidence('stack','v1','stateless','caller-design',Origin.SYNTHETIC))
    design=independent_qmc_design(space,power=3,seed=13)
    trace=propagate(design,owner)
    trace.require_current()
    np.testing.assert_array_equal(trace.values[:,0],[r.hydrogen_production_mol_s for r in seen])
    summary=trace.summarize()
    assert summary.mean[0]>0. and summary.population_variance[0]>0.


@dataclass(frozen=True)
class Case:
    family: str
    connected: tuple[str, ...]
    producer: str
    consumer: str
    scenario: str
    invoke: object


CASES=(
    Case('production.electrolyzer',('production.energy_coupling',),
         'PhotovoltaicElectrolysis.run','charge_linepack_from_electrolysis',
         'actual-PV-production-to-real-gas-linepack-mass-energy-clock-and-identity',_pv_charge),
    Case('production.fuel_cell',(),'Cantera native channel state','run_cantera_synchronized_fuel_cell',
         'actual-channel-state-to-stack-exchange-material-energy-clock',_fuel_cell),
    Case('production.photo',(),'PhotonSupply/PhotoRate','run_photochemical_operation/StoichiometricReaction',
         'adjacent-calculated-optical-conversions-retain-finite-inventory-and-clock',_photo),
    Case('separation.membrane',(),'CanteraFiniteMembraneDevice.run','bind_cantera_membrane_thermostat_heat',
         'native-thermostat-integrals-to-exact-window-duty-and-wrong-clock-rejection',_membrane_heat),
    Case('production.reforming',(),'CanteraCatalyticSurfaceReactor.run','CanteraCatalyticWallHeatAdapter/HeatDuty',
         'actual-wall-heat-to-utility-in-J-on-original-native-clock',_catalytic_heat),
    Case('materials.diffusion',('materials.solubility','materials.permeation'),
         'PowerLawSolubility/steady_permeation/DiffusionSlab','source_from_diffusion_result',
         'calculated-outward-flux-to-interval-H2-source-with-CoolProp-basis',_material_source),
    Case('materials.integrity',('materials.diffusion',),'DiffusionDomain.simulate',
         'radial_hydrogen_eigenstrain_cylinder','explicit-depth-to-radius-concentration-mapping-and-reference-rejection',_diffusion_stress),
    Case('production.microbial_cell',('research.economics',),'FiniteMicrobialCell.run',
         'MicrobialCostProjection/price_window','actual-charge-and-heat-ledger-to-cost-and-clock-rejection',_mec_cost),
    Case('separation.psa',(),'PsaDynaCycle.run','audit_adsorption_cycle',
         'native-cycle-checkpoints-to-inventory-energy-audit-and-clock-rejection',_psa_audit),
    Case('production.thermochemical',(),'FiniteThermochemicalCycle.run',
         'FiniteSolidReactionReactor.run','actual-finite-inventory-to-next-reactor-with-shared-caloric-reference',_thermochemical_solid),
    Case('research.uncertainty',('production.electrolyzer',),'HydrogenStack.evaluate',
         'UncertainModel/propagate/PropagationResult.summarize','computed-molar-output-to-typed-ensemble-statistics',_stack_uncertainty),
)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.family)
def test_actual_module_connection(case,record_property):
    record_property('family',case.family)
    record_property('connected_families',','.join(case.connected))
    record_property('connection_target',case.producer+' -> '+case.consumer)
    record_property('connection_scenario',case.scenario)
    record_property('producer',case.producer)
    record_property('consumer',case.consumer)
    record_property('scope_kind','actual_producer_consumer_contract')
    case.invoke()
