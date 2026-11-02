"""Extreme host arithmetic and physical limits; no external engine validation."""

import importlib.util
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from h2physics.adapters.pv_electrolysis import PVBoundaryProfile, PVBoundarySample
from h2physics.core import Origin
from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry
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
from h2physics.photochemistry import BeerLambertPath, PhotonSupply
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


def stack_limit(mode, current):
    owner = HydrogenStack(StackGeometry(5, .02, .00201588),
        lambda t: ReactionEnergy(200000., 240000., 'authored', 'liquid'), {})
    result = owner.evaluate(current, 300., mode=mode)
    expected = current*.02*5/(2*6.02214076e23*1.602176634e-19)
    if mode == 'fuel_cell':
        expected = -expected
    assert result.hydrogen_production_mol_s == pytest.approx(expected, rel=3e-14, abs=0.)
    assert math.isfinite(result.electric_input_w)
    if current == 0:
        assert result.electric_input_w == result.isothermal_heat_rejection_w == 0.


def optical_limit(depth):
    supply = PhotonSupply.from_lines((500e-9,), (1.,), geometry_id='g', source_id='authored')
    path = BeerLambertPath.uniform(supply, depth_m=depth,
        absorption_coefficient_m_inv=1., reflectance=.25, evidence_id='authored-limit')
    fraction = float(path.absorbed_fraction[0])
    expected = .75*(-math.expm1(-depth))
    assert fraction == pytest.approx(expected, rel=2e-14, abs=0.)
    assert 0 <= fraction <= .75
    assert fraction+float(path.transmitted_fraction[0]) == pytest.approx(.75)


def thermal_limit(extent):
    species = (ChemicalSpecies('water', {'H':2,'O':1}, .018, 'liquid'),
        ChemicalSpecies('H2', {'H':2}, .002, 'gas'), ChemicalSpecies('O2', {'O':2}, .032, 'gas'))
    caloric = FunctionalMolarEnthalpy(species,
        (lambda t,p:-240000., lambda t,p:0., lambda t,p:0.), 'authored', (290.,500.), (1e4,1e6))
    owner = FiniteThermochemicalCycle(caloric,
        ThermochemicalEvidence('original','additive','none','isothermal',Origin.SYNTHETIC))
    reaction = StoichiometricReaction('water-splitting',species,(-1.,1.,.5))
    stage = ThermochemicalStage('edge',0.,1.,'clock',300.,
        (PrescribedConversion(reaction,extent,'authored'),),'authored')
    run = owner.run(ThermochemicalInventory({'water':1.},300.,1e5,'authored'),(stage,),
        carrier_species=('water',),require_carrier_closed=False,require_temperature_closed=False)
    assert run.final.amounts_mol.get('water',0.) == pytest.approx(1.-extent,abs=1e-15)
    assert run.final.amounts_mol.get('H2',0.) == pytest.approx(extent,rel=2e-14,abs=0.)
    assert run.net_heat_required_j == pytest.approx(240000.*extent,rel=2e-14,abs=0.)


def profile_limit(power):
    profile = PVBoundaryProfile('limit','clock',Origin.SYNTHETIC,(
        PVBoundarySample(0.,power,300.,'left'),PVBoundarySample(1e-6,power,300.,'right')))
    stages = profile.stages(stack_temperature_k=300.,maximum_gap_s=1e-6,subdivisions_per_gap=8)
    value = math.fsum((s.end_s-s.start_s)*s.effective_irradiance_w_m2 for s in stages)
    assert value == pytest.approx(power*1e-6,rel=2e-14,abs=0.)
    assert len(stages)==8


def solubility_limit(fugacity):
    law=PowerLawSolubility(HydrogenCarrier('atomic_hydrogen',.001),lambda t:2e-4,.5)
    value=law.concentration_mol_m3(fugacity,300.)
    assert value == pytest.approx(2e-4*math.sqrt(fugacity),rel=2e-14,abs=0.)
    assert math.isfinite(value)


def permeation_limit(up,down,thickness):
    law=PowerLawSolubility(HydrogenCarrier('atomic_hydrogen',.001),lambda t:2e-4,.5)
    result=steady_permeation(law,diffusivity_m2_s=3e-10,thickness_m=thickness,
        upstream_fugacity_pa=up,downstream_fugacity_pa=down,temperature_k=300.)
    expected=3e-10*2e-4*(math.sqrt(up)-math.sqrt(down))/thickness
    assert result.mobile_entity_flux_mol_m2_s == pytest.approx(expected,rel=3e-14,abs=0.)
    assert math.isfinite(result.hydrogen_mass_flux_kg_m2_s)


def diffusion_limit(concentration):
    mesh=DiffusionMesh.planar(.01,10,area_m2=.02)
    model=DiffusionDomain(HydrogenCarrier('atomic_hydrogen',.001),mesh,lambda t:1e-5)
    trace=model.simulate((0.,1.),np.full(10,concentration),
        boundary=lambda t:TransportBoundary(SurfaceCondition('flux',0.),SurfaceCondition('flux',0.)),
        temperature_k=lambda t:300.)
    np.testing.assert_allclose(trace.mobile_mol_m3[-1],concentration,rtol=1e-12,atol=0.)
    assert trace.left_integrated_mol[-1]==trace.right_integrated_mol[-1]==0.
    assert np.all(np.isfinite(trace.mobile_mol_m3))


def stress_limit(pressure):
    result=lame_stress_field(CylinderGeometry(1.,1.000001,'closed','thin-wall-limit'),
        CylinderPressureLoad(pressure,pressure,'equal-pressure',Origin.SYNTHETIC),
        (1.,1.0000005,1.000001),evidence_id='hydrostatic-equal-pressure')
    np.testing.assert_allclose(result.radial_stress_pa,-pressure,rtol=1e-10,atol=0.)
    np.testing.assert_allclose(result.hoop_stress_pa,-pressure,rtol=1e-10,atol=0.)
    assert np.max(result.von_mises_stress_pa) <= max(1e-300,pressure*1e-9)


def uncertainty_limit(scale):
    space=IndependentParameterSpace((ParameterDistribution(Variable('x','coordinate','1','authored'),
        stats.uniform(1.,2.),'uniform','declared',Origin.SYNTHETIC,1.,3.),),'independent','space')
    design=independent_qmc_design(space,power=3,seed=44)
    model=UncertainModel(lambda p:{'y':scale*p['x']},(Variable('y','response','1'),),
        UncertaintyEvidence('linear','v1','stateless','moments',Origin.SYNTHETIC))
    run=propagate(design,model)
    if scale==1e-200:
        with pytest.raises(ValueError,match='variance underflow'):
            run.summarize()
    elif scale==1e200:
        with pytest.raises(ValueError,match='nonfinite arithmetic'):
            run.summarize()
    else:
        summary=run.summarize((0.,1.))
        assert summary.population_variance[0]==0.
        assert summary.mean[0]==0.


def psa_limit(scale):
    # Only the host totals function is called on explicit component ledger inputs.
    # These arrays are not represented as issued native cycle outputs.
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('extreme_psa_inputs',root/'tests/test_psa_cycle.py')
    inputs=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inputs)
    owner=inputs.adapter()
    feed=np.array([scale,scale])
    product=np.array([scale,0.])
    tail=np.zeros(2)
    result=owner._totals(feed,product,tail,css=False)
    if scale==0:
        assert result.hydrogen_product_purity is None
        assert result.hydrogen_product_to_feed_ratio is None
    else:
        assert result.hydrogen_product_purity==1.
        assert result.hydrogen_product_to_feed_ratio==1.
    assert result.css_hydrogen_recovery is None


def economics_limit(quantity,rate):
    from h2physics.adapters.physical_economics import (
        PhysicalCostProjection,
        QuantityBoundary,
        ReportingWindow,
        SourceSnapshot,
        UtilityTariff,
    )
    source=(quantity,.01)
    window=ReportingWindow(0.,1.,'clock','explicit-synthetic-ledger','generated_h2_kg')
    class Adapter:
        identifier='explicit-limit-ledger'
        def snapshot(self,source,window,hydrogen_id):
            q={'electrical_work_into_j':source[0],'generated_h2_kg':source[1]}
            boundaries={name:QuantityBoundary(name,name+'-boundary','authored','synthetic-input',
                (name,) if name.endswith('_j') else ()) for name in q}
            return SourceSnapshot(source,window,hydrogen_id,self.identifier,'explicit-input',q,boundaries,
                (),source,(source,))
    projection=PhysicalCostProjection.from_source(source,Adapter(),window,hydrogen_id='H2')
    tariff=UtilityTariff('electrical_work_into_j',rate,'USD',2020,'declared',
        'electrical_work_into_j-boundary',Origin.SYNTHETIC)
    result=projection.price_window((tariff,))
    assert result.total_usd==pytest.approx(quantity*rate,rel=2e-14,abs=0.)
    assert math.isfinite(result.total_usd)


def microbial_limit(duration):
    from examples.microbial_cell import build_problem
    owner,initial,stages=build_problem()
    stage=replace(stages[0],end_s=duration)
    trace=owner.run(initial,(stage,))
    expected=trace.steps[0].current_a*duration/(2*6.02214076e23*1.602176634e-19)
    assert trace.hydrogen_generated_mol==pytest.approx(expected,rel=1e-8,abs=0.)
    assert 0 < trace.hydrogen_generated_mol < initial.amounts_mol['substrate']*2


def gasification_limit(amount):
    import cantera as ct

    from h2physics.adapters.cantera_multiphase import _snapshot
    phase=ct.Solution('h2o2.yaml')
    phase.TPX=500.,101325.,{'H2':1.}
    mixture=ct.Mixture([(phase,amount/1000.)])
    result=_snapshot(mixture,phase.element_names)
    expected=amount*phase.molecular_weights[phase.species_index('H2')]/1000.
    assert result.mass_kg==pytest.approx(expected,rel=2e-14,abs=0.)
    assert np.all(np.isfinite(result.species_mol))


def surface_energy_limit(amount):
    import cantera as ct

    from h2physics.adapters.cantera_surface_reactor import _surface_internal_energy_j
    surface=ct.Interface('ptcombust.yaml','Pt_surf')
    surface.TP=900.,101325.
    inventory=np.full(surface.n_species,amount)
    expected=math.fsum(amount*float(h)/1000. for h in surface.partial_molar_enthalpies)
    value=_surface_internal_energy_j(surface,inventory)
    assert value==pytest.approx(expected,rel=2e-14,abs=0.)
    assert math.isfinite(value)


def biological_limit(hydrogen_mol_m3):
    import sys
    root=Path(__file__).resolve().parents[1]
    for directory in reversed(('native_biological_core_fixed','native_biological_packages')):
        target=str(root/'artifacts'/directory)
        if target not in sys.path:
            sys.path.insert(0,target)
    from h2physics.adapters.biological import QsdSanNative
    from scripts.check_biological import make_case
    owner=make_case(QsdSanNative.from_installed())
    state=np.array([owner.initial_liquid[k] for k in owner._ids]+[
        owner.initial_gas[k]/1000. for k in owner.native_model._biogas_IDs]+[0.])
    state[len(owner._ids)]=hydrogen_mol_m3/1000.
    point=owner._point(864000.,state)
    h2=owner._ids.index('S_h2')
    expected=.005*hydrogen_mol_m3*float(owner.native_components.chem_MW[h2])/1000.
    assert point.headspace_hydrogen_kg==pytest.approx(expected,rel=2e-14,abs=0.)
    assert math.isfinite(point.headspace_hydrogen_kg)


def membrane_limit(length):
    import hashlib

    import cantera as ct

    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_membrane import (
        CanteraDustyGasTransport,
        MembraneEndpoint,
        MembraneTransportEvidence,
        PorousTransportGeometry,
    )
    raw=(Path(ct.__file__).parent/'data/h2o2.yaml').read_bytes()
    names=('H2','N2','AR')
    species={v.name:v for v in ct.Species.list_from_yaml(raw.decode(),section='species')}
    def factory():
        return ct.Solution(thermo='ideal-gas',species=[species[n] for n in names],
            transport_model='multicomponent')
    basis=MechanismBasis('installed-native',hashlib.sha256(raw).hexdigest(),'Cantera-BSD-3-Clause',
        ('https://cantera.org/3.2/',),300.,1000.,.001,2e5)
    owner=CanteraDustyGasTransport(factory,basis,evidence=MembraneTransportEvidence(
        'installed','warm','ideal-gas','native-reference','spin-unresolved'))
    geometry=PorousTransportGeometry(.35,2.5,50e-9,0.,length,'geometry','authored',Origin.SYNTHETIC)
    def endpoint(side,fractions):
        return MembraneEndpoint(330.,101325.,names,fractions,'mole',side,'warm','geometry','authored',Origin.SYNTHETIC)
    result=owner.flux(endpoint('left',(.7,.2,.1)),endpoint('right',(.4,.5,.1)),geometry)
    expected=np.asarray(result.native_flux_kmol_m2_s)*1000.
    np.testing.assert_allclose(result.molar_flux_mol_m2_s,expected,rtol=2e-14,atol=0.)
    assert np.all(np.isfinite(result.mass_flux_kg_m2_s))
    assert np.any(abs(expected)>0.)


def stack_overflow(mode):
    owner=HydrogenStack(StackGeometry(5,1e200,.00201588),
        lambda t:ReactionEnergy(200000.,240000.,'authored','liquid'),{})
    with pytest.raises(ValueError,match='finite'):
        owner.evaluate(1e200,300.,mode=mode)


def solubility_overflow():
    law=PowerLawSolubility(HydrogenCarrier('atomic_hydrogen',.001),lambda t:1e200,2.)
    with pytest.raises(ValueError,match='finite|representation'):
        law.concentration_mol_m3(1e200,300.)


@dataclass(frozen=True)
class ExtremeCase:
    family:str
    scenario:str
    target:str
    invoke:object
    scope:str='model_equation'

CASES=[]
for mode,family in [('electrolysis','production.electrolyzer'),('fuel_cell','production.fuel_cell')]:
    for current in (0.,1e-150,1e100):
        CASES.append(ExtremeCase(family,f'current-density-{current}','HydrogenStack.evaluate',lambda m=mode,c=current:stack_limit(m,c)))
for depth in (0.,1e-16,1e6):
    CASES.append(ExtremeCase('production.photo',f'optical-depth-{depth}','BeerLambertPath.absorbed_fraction',lambda x=depth:optical_limit(x)))
for extent in (0.,1.):
    CASES.append(ExtremeCase('production.thermochemical',f'conversion-{extent}','FiniteThermochemicalCycle.run',lambda x=extent:thermal_limit(x)))
for power in (0.,1e-100,1e100):
    CASES.append(ExtremeCase('production.energy_coupling',f'irradiance-{power}','PVBoundaryProfile.stages',lambda x=power:profile_limit(x),'supporting_geometry_or_accounting'))
for fugacity in (0.,1e-200,1e200):
    CASES.append(ExtremeCase('materials.solubility',f'fugacity-{fugacity}','PowerLawSolubility.concentration_mol_m3',lambda x=fugacity:solubility_limit(x)))
for up,down,thickness in ((1e5,1e5,.01),(0.,1e5,.01),(1e-100,0.,1e-10)):
    CASES.append(ExtremeCase('materials.permeation',f'pressures-{up}-{down}-thickness-{thickness}','steady_permeation',lambda u=up,d=down,t=thickness:permeation_limit(u,d,t)))
for concentration in (0.,1e-100,1e100):
    CASES.append(ExtremeCase('materials.diffusion',f'sealed-uniform-{concentration}','DiffusionDomain.simulate',lambda x=concentration:diffusion_limit(x)))
for pressure in (0.,1e-100,1e100):
    CASES.append(ExtremeCase('materials.integrity',f'thin-equal-pressure-{pressure}','lame_stress_field',lambda x=pressure:stress_limit(x)))
for scale in (0.,1e-200,1e200):
    CASES.append(ExtremeCase('research.uncertainty',f'output-scale-{scale}','PropagationResult.summarize',lambda x=scale:uncertainty_limit(x),'supporting_geometry_or_accounting'))
for scale in (0.,1e-150,1e150):
    CASES.append(ExtremeCase('separation.psa',f'component-ledger-{scale}','PsaDynaCycle._totals',lambda x=scale:psa_limit(x),'supporting_geometry_or_accounting'))
for quantity,rate in ((0.,.001),(1e-150,1e100),(1e150,1e-100)):
    CASES.append(ExtremeCase('research.economics',f'quantity-{quantity}-rate-{rate}','PhysicalCostProjection.price_window',lambda q=quantity,r=rate:economics_limit(q,r),'supporting_geometry_or_accounting'))
for duration in (1e-6,1e-3):
    CASES.append(ExtremeCase('production.microbial_cell',f'finite-duration-{duration}','FiniteMicrobialCell.run',lambda t=duration:microbial_limit(t)))

for amount in (1e-150,1e150):
    CASES.append(ExtremeCase('production.gasification',f'host-native-amount-{amount}','cantera_multiphase._snapshot',lambda x=amount:gasification_limit(x),'supporting_geometry_or_accounting'))
for amount in (0.,1e-150,1e150):
    CASES.append(ExtremeCase('production.reforming',f'surface-inventory-{amount}','_surface_internal_energy_j',lambda x=amount:surface_energy_limit(x),'supporting_geometry_or_accounting'))
for amount in (0.,1e-150):
    CASES.append(ExtremeCase('production.biological',f'headspace-H2-{amount}','QsdSanAdm1Digester._point',lambda x=amount:biological_limit(x),'supporting_geometry_or_accounting'))
for length in (1e-100,1e100):
    CASES.append(ExtremeCase('separation.membrane',f'path-length-{length}','CanteraDustyGasTransport.flux host unit conversion',lambda x=length:membrane_limit(x),'supporting_geometry_or_accounting'))
for mode,family in [('electrolysis','production.electrolyzer'),('fuel_cell','production.fuel_cell')]:
    CASES.append(ExtremeCase(family,'finite-input-overflow-rejection','HydrogenStack.evaluate',lambda m=mode:stack_overflow(m)))
CASES.append(ExtremeCase('materials.solubility','finite-input-overflow-rejection','PowerLawSolubility.concentration_mol_m3',solubility_overflow))

@pytest.mark.parametrize('case',CASES,ids=lambda c:c.family+':'+c.scenario)
def test_extreme_host_contract(case,record_property):
    record_property('family',case.family)
    record_property('extreme_scenario',case.scenario)
    record_property('extreme_target',case.target)
    record_property('scope_kind',case.scope)
    case.invoke()
