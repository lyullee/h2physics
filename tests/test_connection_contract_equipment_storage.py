"""Actual producer-to-consumer handoffs; native prediction accuracy is excluded."""

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "artifacts/native_packages", ROOT / "artifacts/underground_provider_review/uh2sc/src", ROOT / "scripts"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def validation(module, name, tmp_path, **parameters):
    outcome = getattr(importlib.import_module("validation.cases." + module), name)(
        work_directory=tmp_path, **parameters)
    assert outcome.accepted
    assert outcome.metrics


def supply(tmp_path):
    del tmp_path
    from check_finite_supply import run_case
    trace, row, margin = run_case(.01, use_low_level=True)
    assert trace.clock_id == "authored-finite-supply-zero"
    assert row[2] > 0. and margin > 0.
    assert abs(row[5]) < 1e-8 and abs(row[6]) < .01


def instrument(tmp_path):
    del tmp_path
    from examples.finite_transfer import build_model, schedule
    from h2physics.adapters.lh2dt_instrumentation import Lh2dtTransmitter, TransmitterEvidence
    from h2physics.core import Origin, TimeSeries
    from h2physics.observations import Variable
    native = importlib.import_module("lh2dt.instrumentation")
    owner = build_model()
    trace = owner.run(schedule(owner), clock_id="authored-transfer-clock", maximum_step_s=.1,
        clock_tolerance_s=1e-10, isolate_on_completion=True)
    node = owner.receiver.node_id
    values = np.array([point.local_run.steps[-1].equipment.node_states[node].pressure_pa
        for point in trace.points])[:, None]
    times = np.array([point.time_s for point in trace.points])
    series = TimeSeries(times, values, ("pressure",), ("Pa",), np.ones_like(values,dtype=bool),
        trace.clock_id, Origin.PREDICTED, "accepted-native-tank-pressure", ("pressure",), ("absolute",))
    config = TransmitterEvidence("pressure", node, Variable("pressure","pressure","Pa","absolute"),
        "declared-calibration","declared-response",("synthetic",),Origin.SYNTHETIC)
    sensor = Lh2dtTransmitter(native.FirstOrderTransmitter(native.TransmitterParameters(
        lower_range=0.,upper_range=1e7,time_constant_s=.1)),evidence=config)
    result = sensor.run(series, channel="pressure", initial_native_state=sensor.initialize(values[0,0]),
        initial_time_s=float(times[0]),location_id=node)
    assert result.input_series is series
    assert result.prediction.clock_id == series.clock_id
    np.testing.assert_array_equal(result.prediction.time_s, series.time_s)
    assert result.evidence.variable.unit == "Pa"
    with pytest.raises(ValueError):
        sensor.run(series,channel="pressure",initial_native_state=sensor.initialize(values[0,0]),
            initial_time_s=float(times[0]),location_id="foreign-location")


def spin(tmp_path):
    del tmp_path
    from check_spin_integration import model, reference
    native = importlib.import_module("lh2dt.ortho_para")
    owner = model(native)
    trace = owner.thermostat(owner.state(.25),temperature_k=20.,mass_kg=.01,pressure_pa=1000.,
        time_s=(10.,11.,12.),clock_id="spin-calorimetry-clock",pressure_evidence_id="declared",
        enthalpy_reference=reference())
    assert trace.samples[-1].time_s==12.
    assert all(abs(point.enthalpy_balance_residual_j)<1e-8 for point in trace.samples)
    assert trace.samples[-1].cumulative_external_heat_j < 0.


def microsphere(tmp_path):
    del tmp_path
    from h2physics.materials import HydrogenCarrier, PowerLawSolubility, SurfaceCondition
    from h2physics.storage.finite_hydride import HydrideGasThermodynamics
    from h2physics.storage.microsphere import MicrosphereDomain, MicrosphereStorage
    gas=HydrideGasThermodynamics.coolprop("Hydrogen")
    model=MicrosphereStorage(inner_radius_m=1e-5,outer_radius_m=1.1e-5,cells=8,
        diffusivity_m2_s=lambda t:1e-14,
        solubility=PowerLawSolubility(HydrogenCarrier("molecular_hydrogen",gas.molar_mass_kg_mol),lambda t:1e-5,1.),
        gas=gas,domain=MicrosphereDomain(200.,600.,1.,1e7,1e-20),parameter_evidence="authored-no-material-fit")
    initial=gas.state_pt(1e5,300.)
    amount=initial.density_kg_m3*model.cavity_volume_m3/gas.molar_mass_kg_mol
    trace=model.simulate((0.,.5,1.),amount,np.zeros(8),temperature_k=lambda t:300.,
        external_wall_condition=lambda t,temp:SurfaceCondition("flux",0.),clock_id="shared-transport-clock",
        boundary_evidence="sealed-outer-wall",maximum_step_s=.1)
    assert trace.clock_id=="shared-transport-clock"
    assert trace.transport.wall_inventory_mol[-1]>0.
    np.testing.assert_allclose(trace.total_hydrogen_mass_kg,trace.total_hydrogen_mass_kg[0],rtol=1e-10,atol=0.)
    assert max(abs(trace.gas_transfer_residual_mol)) < amount*1e-10
    assert trace.gas_states[-1].basis==initial.basis


def mixture(tmp_path):
    del tmp_path
    from math import fsum

    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureProperties, MixtureInventoryStateAdmission
    gas=CoolPropMixtureProperties(GasComposition("mixture-handoff",("H2","N2"),(.5,.5),(.00201588,.0280134)),
        fluid_names={"H2":"Hydrogen","N2":"Nitrogen"})
    packet=gas.phase_partition_pq(5e6,1.,component_mole_balance_tolerance=1e-7)
    amounts=packet.split_moles(2.)
    receipt=MixtureInventoryStateAdmission(gas,packet,amounts.component_moles,
        amounts.total_internal_energy_j,fsum(amounts.phase_volumes_m3),1e-7,1e-12,1e-6,"accepted-provider-packet")
    assert receipt.require_current() is receipt
    assert max(abs(v) for v in receipt.component_mole_residuals)<1e-7


def reliquefier(tmp_path):
    del tmp_path
    import test_lh2dt_reliquefier as fixture

    from h2physics.adapters.reliquefier_product import (
        CollectedProductInventory,
        FiniteColdReservoir,
        FiniteReliquefierProduct,
        ProductWindow,
        ReliquefierProductPorts,
    )
    provider,owner=fixture.steady(1e5)
    result=owner.evaluate(provider.saturated(2e5,1.),outlet_pressure_pa=2e5,mass_flow_kg_s=.001)
    result.require_current()
    consumer=FiniteReliquefierProduct(ReliquefierProductPorts("feed","product","return","vent"))
    receipt=consumer.collect_steady(result,ProductWindow("recovery-clock",10.,11.),collected_product_kg=.001,
        returned_kg=0.,vented_kg=0.,product=CollectedProductInventory(result.outlet.basis,0.,0.),
        cold=FiniteColdReservoir("cold",1e8,1e8,"declared-cold-budget"))
    assert receipt.require_current() is receipt
    assert receipt.product_after.mass_kg==.001
    assert receipt.product_after.basis==result.outlet.basis
    assert receipt.cold_duty.removed_heat_j == pytest.approx(-result.power.heat_w,rel=1e-12,abs=0.)


def insulation(tmp_path):
    del tmp_path
    from check_insulation_integration import make_tank
    modules=tuple(importlib.import_module("lh2dt."+name) for name in
        ("vacuum_insulation","layered_tank","geometry","properties"))
    tank,initial,boundary,allocation,reader=make_tank(modules,wall_only=True)
    seen=[]
    callback=boundary.layered_wall_callback(allocation,warm_temperature_k=lambda t,th:280.,
        vacuum_pressure_pa_abs=0.,clock_id="insulation-clock",start_time_s=7.,
        observer=lambda t,result:seen.append((t,result)))
    trace=tank.simulate(initial,.2,.1,280.,wall_heat_callback=callback)
    assert seen and seen[0][0]==7.
    assert seen[-1][0]==pytest.approx(7.2)
    before,after=reader(initial),reader(trace[-1].state)
    assert after.solid_internal_energy_j>before.solid_internal_energy_j
    assert after.total_energy_j-before.total_energy_j==pytest.approx(trace[-1].cumulative_boundary_energy_J,rel=1e-8,abs=1e-7)


def cryo(tmp_path):
    del tmp_path
    from check_cryo_compressed import build, run

    from h2physics.adapters.cryo_compressed import CryoCompressedNative
    owner=build(CryoCompressedNative.from_installed(source_id="reviewed-native"))
    trace=run(owner,step=.05,duration=.1,power=100.)
    assert trace.boundary.clock_id=="authored-operation-clock"
    assert trace.points[-1].fluid.basis==owner.properties.basis
    assert abs(trace.points[-1].balance.energy_residual_j)<1e-5


def thermal_compressor(tmp_path):
    del tmp_path
    from check_hydride_compressor import make_case, stages

    from h2physics.storage.hydride import HydrideState
    owner=make_case(solid_capacity=50.)
    trace=owner.run(stages(owner,durations=(.02,.02,.02,.02)),initial_solid=HydrideState(.01,300.),
        initial_bed_gas=owner.bed.gas.state_pt(2e5,300.),sample_interval_s=.01,maximum_step_s=.005)
    trace.require_current()
    assert len(trace.segments)==4
    assert all(abs(p.total_hydrogen_residual_kg)<1e-10 for p in trace.points)
    assert all(abs(p.total_energy_residual_j)<1e-4 for p in trace.points)


def vent(tmp_path):
    del tmp_path
    import test_formula_contract_equipment_storage as fixture

    from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
    from h2physics.adapters.lh2dt_vent import Lh2dtVentStack, VentEnvelope
    from h2physics.facility_continuity import (
        ExternalFacilityRate,
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
    )
    direct,low,bridge,state_type=fixture._real_native_properties()
    native=fixture._native_state_type("vent_stack","VentStack")(2.,.002,0.,properties=low,
        ambient_temperature_K=310.,ambient_UA_W_K=0.)
    def viscosity(state):
        return direct.state_ph(state.pressure_Pa,state.specific_enthalpy_J_kg).viscosity_pa_s
    pipe=Lh2dtDarcyPipe(native.pipe,bridge,viscosity_reader=viscosity,
        friction_law=lambda re,rough:64./re,friction_law_id="explicit-reference-laminar",
        result_factory=fixture._native_state_type("pipe","PipeResult"))
    owner=Lh2dtVentStack(native,bridge,state_factory=state_type,
        envelope=VentEnvelope(1e4,1e7,80.,1000.,.1,.1,.3,"authored"),component_id="vent",evidence_id="authored",
        allow_reverse=False,viscosity_reader=viscosity,sound_speed_reader=lambda st:direct.state_ph(
            st.pressure_Pa,st.specific_enthalpy_J_kg).speed_of_sound_m_s,
        sound_speed_capability_id="actual-provider",hydraulic_pipe=pipe)
    left,right=direct.state_pt(2e5,300.),direct.state_pt(2e5-10.,300.)
    result=owner.evaluate(left,right,left_node="left",right_node="right",left_port_id="out",right_port_id="in")
    row=result.transfer
    flow=row.mass_flow_kg_s
    frame=FacilityContinuityFrame("vent-application-clock",1.,(row,),(
        ExternalFacilityRate("feed","left","external-feed",flow,row.upstream),
        ExternalFacilityRate("exhaust","right","external-exhaust",-flow,row.transmitted)))
    audit=FacilityContinuityAudit((FacilityNode("left",direct.basis),FacilityNode("right",direct.basis))).audit(frame)
    assert audit.mass_residual_kg_s==0.
    assert abs(audit.node_energy_residual_w)<1e-8
    assert frame.transfers[0] is result.transfer


def porous(tmp_path):
    del tmp_path
    from h2physics.adapters.lh2dt_instrumentation import Lh2dtTransmitter, TransmitterEvidence
    from h2physics.core import Origin, TimeSeries
    from h2physics.observations import Variable
    from h2physics.storage.porous_reservoir import (
        PorousReservoir,
        PorousReservoirGeometry,
        PorousReservoirSchedule,
    )
    from h2physics.thermo import CoolPropProperties
    geometry=PorousReservoirGeometry((1.,2.,3.),1.,(.2,.2),(1e-12,1e-12),(300.,300.),"authored")
    owner=PorousReservoir.from_property_provider(geometry=geometry,property_provider=CoolPropProperties("Hydrogen"),property_evidence_id="native-HEOS")
    trace=owner.run(PorousReservoirSchedule((0.,.01,.02),(2e5,2e5),1e4,1e7,(0.,0.,0.),"porous-clock"))
    trace.require_current()
    values=trace.pressure_pa[:,0:1]
    series=TimeSeries(trace.time_s,values,("pressure",),("Pa",),np.ones_like(values,dtype=bool),
        "porous-clock",Origin.PREDICTED,"reservoir-result",("pressure",),("absolute",))
    native=importlib.import_module("lh2dt.instrumentation")
    owner=Lh2dtTransmitter(native.FirstOrderTransmitter(native.TransmitterParameters(
        lower_range=0.,upper_range=1e7,time_constant_s=0.)),evidence=TransmitterEvidence("s","well",
            Variable("pressure","pressure","Pa","absolute"),"authored","instantaneous",("synthetic",),Origin.SYNTHETIC))
    result=owner.run(series,channel="pressure",initial_native_state=owner.initialize(float(values[0,0])),
        initial_time_s=0.,location_id="well")
    assert result.input_series is series
    assert result.prediction.clock_id==series.clock_id
    np.testing.assert_allclose(result.prediction.values[:,0],values[:,0],rtol=1e-14,atol=0.)


def binding_guards(tmp_path):
    del tmp_path
    from dataclasses import replace

    import test_finite_hydride as fixture

    from h2physics.storage.hydride import HydrideState
    bed=fixture.model()
    trace=fixture.simulate(bed,solid=HydrideState(.5,300.),times=np.array((10.,10.01,10.02)),step=.002)
    trace.require_current()
    native_state=trace.snapshots[0].gas
    pressure=native_state.pressure_pa
    object.__setattr__(native_state,"pressure_pa",pressure*(1.+5e-13))
    try:
        with pytest.raises(ValueError,match="gas state changed after issuance"):
            trace.require_current()
    finally:
        object.__setattr__(native_state,"pressure_pa",pressure)
    trace.require_current()
    original=trace.gas_thermodynamics
    def changed(p,t):
        state=original.state_pt(p,t)
        return replace(state,density_kg_m3=state.density_kg_m3*1.01)
    object.__setattr__(trace,"gas_thermodynamics",replace(original,state_pt=changed))
    try:
        with pytest.raises(ValueError,match="gas provider"):
            trace.require_current()
    finally:
        object.__setattr__(trace,"gas_thermodynamics",original)
    trace.require_current()
    from h2physics.storage.adsorption_dynamics import AdsorptionBoundaryRates
    from validation.cases.adsorption_dynamics import _inputs
    inputs=_inputs(lambda st:AdsorptionBoundaryRates(0.,0.,0.,0.,"zero","reference"),end=1.,boundaries=(0.,1.))
    for _ in range(3):
        inputs.require_current()
    callback=inputs.boundary_rates
    def replacement(st):return callback(st)
    object.__setattr__(inputs,"boundary_rates",replacement)
    with pytest.raises(ValueError,match="callback bindings"):
        inputs.require_current()


def adsorption(tmp_path):
    del tmp_path
    from dataclasses import replace

    import test_finite_hydride as bed_fixture

    from h2physics.adapters.adsorption_finite_hydride_port import bind_adsorption_to_finite_hydride
    from h2physics.adapters.finite_adsorption_vessel import FiniteAdsorptionVessel, FrozenGasBinding
    from h2physics.storage.adsorption_dynamics import (
        AdsorptionBoundaryRates,
        integrate_adsorption_dynamics,
    )
    from h2physics.storage.hydride import HydrideState
    from h2physics.thermo import CoolPropProperties
    from validation.cases.adsorption_dynamics import _inputs
    provider=CoolPropProperties("Hydrogen")
    reference=provider.basis.reference_id
    def outlet(state):
        return AdsorptionBoundaryRates(0.,0.,1e-4,0.,"prescribed-real-gas-outlet",reference)
    seed=_inputs(outlet,end=.02,boundaries=(0.,.02))
    bed=bed_fixture.model()
    binding=FrozenGasBinding.bind(provider,species=("H2",),mole_fractions=(1.,),
        molar_masses_kg_mol=(bed.gas.molar_mass_kg_mol,),composition_id="pure-normal-H2")
    vessel=FiniteAdsorptionVessel(vessel_id="native-property-vessel",geometry=seed.vessel.geometry,
        adsorption=seed.vessel.adsorption,gas=binding)
    source=integrate_adsorption_dynamics(replace(seed,vessel=vessel))
    assert source.status=="completed",source.status
    source.require_current()
    states=tuple(provider.state_pt(float(p),float(t)) for p,t in zip(source.pressure_pa[:-1],source.temperature_k[:-1],strict=True))
    port=bind_adsorption_to_finite_hydride(source,bed.gas,stream_states=states,clock_id="adsorption-bed-clock",
        clock_alignment_evidence_id="same-second-origin",hydraulic_transfer_evidence_id="prescribed-direct-port-no-line-solver",
        state_projection_evidence_ids=tuple("accepted-source-state" for _ in states),absolute_enthalpy_tolerance_j=1e-4,
        relative_enthalpy_tolerance=1e-4)
    trace=bed.simulate(source.time_s,HydrideState(.1,300.),bed.gas.state_pt(3e5,300.),
        boundary=bed_fixture.boundary(start=0.,end=.02,clock=port.clock_id),clock_id=port.clock_id,
        maximum_step_s=.002,gas_port=port.boundary)
    trace.require_current()
    port.require_current()
    expected=float(source.cumulative_outlet_mol[-1])*bed.gas.molar_mass_kg_mol
    assert trace.integrated_external_gas_mass_kg[-1]==pytest.approx(expected,rel=1e-9,abs=0.)
    assert trace.gas_port_boundary is port.boundary
    original_pressure=states[0].pressure_pa
    object.__setattr__(states[0],"pressure_pa",original_pressure*(1.+5e-13))
    try:
        with pytest.raises(ValueError,match="projection or owner changed"):
            port.require_current()
    finally:
        object.__setattr__(states[0],"pressure_pa",original_pressure)
    port.require_current()
    wrong=(provider.state_pt(float(source.pressure_pa[0])*1.01,float(source.temperature_k[0])),*states[1:])
    with pytest.raises(ValueError,match="Outlet state must match"):
        bind_adsorption_to_finite_hydride(source,bed.gas,stream_states=wrong,clock_id="adsorption-bed-clock",
            clock_alignment_evidence_id="same-second-origin",hydraulic_transfer_evidence_id="prescribed-direct-port-no-line-solver",
            state_projection_evidence_ids=tuple("accepted-source-state" for _ in states),absolute_enthalpy_tolerance_j=1e-4,
            relative_enthalpy_tolerance=1e-4)


def underground(tmp_path):
    from unittest.mock import patch

    from examples.underground_storage import authored_inputs
    def single_volume(**kwargs):
        inputs=authored_inputs(**kwargs)
        inputs["wells"]["well"]["control_volume_length"]=inputs["wells"]["well"]["pipe_lengths"][0]
        inputs["wells"]["well"]["valves"]["operation"]["reservoir"]["pressure"]=6e6
        return inputs
    with patch("examples.underground_storage.authored_inputs",single_volume):
        validation("underground_compressor_inlet","validate_inlet",tmp_path)


@dataclass(frozen=True)
class ConnectionCase:
    family: str
    connected: tuple[str,...]
    module: str
    function: str
    producer: str
    consumer: str
    scenario: str
    invoke: object=None
    parameters: object=None


CASES = (
    ConnectionCase("equipment.lh2_tank",("equipment.pump","equipment.two_phase_pipe","equipment.vaporizer","equipment.valve"),
        "","","native finite tank/pump/pipe/vaporizer","shared supply network + accepted inventory/rate ledgers",
        "scheduled isolation preserves mass energy and residual downstream inventory",supply),
    ConnectionCase("equipment.gas_tank",("equipment.valve","thermo.pure_fluid"),
        "finite_transfer","validate_product_receipt","actual finite two-tank run","product_delivery_from_finite_transfer",
        "accepted receiver mass becomes exact-window kg/s receipt",parameters={"with_line":False}),
    ConnectionCase("equipment.compressor",("equipment.gas_tank",),"lh2dt_compressor","validate_source",
        "accepted native tank source","Lh2dtCompressorStage.evaluate","original source state clock and enthalpy enter compressor"),
    ConnectionCase("equipment.heat_exchanger",(),"lh2dt_heat_exchanger","validate_wall_transfer_series",
        "actual two-side finite heat exchanger","wall_transfer_series","signed heat windows retain exact common clock and reject stale copy"),
    ConnectionCase("storage.adsorption",("storage.adsorption_thermal","storage.hydride_dynamic","storage.hydride_equilibrium"),
        "","","computed CoolProp-backed adsorption dynamics","bind_adsorption_to_finite_hydride + FiniteHydrideBed",
        "component mass enthalpy and state clocks match finite bed inlet",adsorption),
    ConnectionCase("storage.hydride_dynamic",("equipment.compressor",),"finite_hydride_compressor_inlet","validate_handoff",
        "accepted finite hydride withdrawal","actual compressor runs + bind_finite_hydride_to_compressor",
        "every bed withdrawal interval matches compressor mass enthalpy and clock"),
    ConnectionCase("storage.solid_reaction",(),"solid_reaction","validate_heat_utility_handoff",
        "completed finite solid reaction","HeatDuty.bind + SolidReactionHeatAdapter",
        "external reaction heat enters heat-duty window with caloric ownership and stale rejection"),
    ConnectionCase("storage.carrier_reaction",(),"carrier_conversion","validate_packet",
        "completed carrier reaction actual prewithdrawal","receiver CarrierConversion.run",
        "withdrawn H2 finite packet enters receiver; duplicate takeoff and frame mutation reject"),
    ConnectionCase("thermo.mixtures",(),"","",
        "actual CoolProp mixture dew-endpoint partition","MixtureInventoryStateAdmission",
        "component moles energy volume and native owner survive admission",mixture),
    ConnectionCase("equipment.relief",(),"finite_relief_lift","validate_finite_source_handoff",
        "owner-issued relief withdrawal ledger","finite source handoff",
        "accepted relief edges become finite source with phase clock and inventory ownership"),
    ConnectionCase("equipment.instrument",(),"","","computed finite receiver tank pressure","Lh2dtTransmitter.run",
        "actual Pa absolute prediction time series enters selected native sensor",instrument),
    ConnectionCase("thermo.spin",(),"","","actual native spin kinetic state","thermostat enthalpy calorimeter",
        "spin composition conversion heat and held-clock calorimetry retain balance",spin),
    ConnectionCase("storage.microsphere",(),"","","CoolProp finite cavity state","shared spherical DiffusionDomain + cavity feedback",
        "finite gas mass transferred into sealed wall retains species basis and total inventory",microsphere),
    ConnectionCase("equipment.reliquefier",(),"","","actual native steady reliquefier","FiniteReliquefierProduct.collect_steady",
        "computed liquid product and cold duty become finite collection ledger",reliquefier),
    ConnectionCase("equipment.insulation",("equipment.lh2_tank",),"","","actual native insulation heat","layered tank wall callback and inventory reader",
        "absolute heat clock allocation closes finite wall energy",insulation),
    ConnectionCase("storage.cryo_compressed",(),"","","native cryo tank relief integration","cryo state and energy audit",
        "finite native rows retain fluid basis clock and global energy ledger",cryo),
    ConnectionCase("storage.hydride_compressor",(),"","","finite hydride bed and actual native source/receiver vessels","HydrideThermalCompressor.run",
        "all-body gas/solid mass and energy close over staged thermal schedule",thermal_compressor),
    ConnectionCase("equipment.gas_pipe",(),"real_gas_linepack_fuel_cell_feed","validate_feed",
        "CoolProp real-gas finite linepack withdrawal","fuel cell feed conditioning adapter",
        "accepted source mass energy reference clock and H2 identity map into fuel cell"),
    ConnectionCase("equipment.vent",("facility.network",),"","","actual native vent and shared hydraulic transfer","FacilityContinuityAudit.audit",
        "original vent transfer with actual enthalpies closes at both facility nodes",vent),
    ConnectionCase("storage.porous_reservoir",(),"","","computed CoolProp-backed porous pressure history","Lh2dtTransmitter.run",
        "explicit Pa absolute observation projection preserves reservoir output clock and values",porous),
    ConnectionCase("storage.hydride_dynamic",("storage.adsorption_thermal",),"","","genuine accepted finite bed and admitted adsorption callbacks","trace/input require_current guards",
        "native reflashes remain current while1percent density and callback substitutions are rejected",binding_guards),
)


@pytest.mark.parametrize("case",CASES,ids=lambda c:c.family+"::"+c.consumer)
def test_actual_module_connection(case,tmp_path,record_property):
    record_property("family",case.family)
    record_property("connected_families",",".join(case.connected))
    record_property("connection_target",case.producer+" -> "+case.consumer)
    record_property("connection_scenario",case.scenario)
    record_property("producer",case.producer)
    record_property("consumer",case.consumer)
    record_property("scope_kind","actual_host_handoff")
    if case.invoke is not None:
        case.invoke(tmp_path)
    else:
        validation(case.module,case.function,tmp_path,**(case.parameters or {}))
