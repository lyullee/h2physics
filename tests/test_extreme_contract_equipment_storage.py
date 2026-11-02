"""Selected host extremes; native property predictions are not accuracy targets."""

import math
from dataclasses import dataclass, replace

import numpy as np
import pytest
import test_formula_contract_equipment_storage as nominal

from h2physics.adapters.lh2dt_compressor import CompressorEnvelope
from h2physics.adapters.lh2dt_dynamics import lumped_inventory_reader, stratified_inventory_reader
from h2physics.adapters.lh2dt_insulation import layered_inventory_reader
from h2physics.adapters.lh2dt_pump_operation import PumpSpeedActuator
from h2physics.adapters.lh2dt_spin import SpinEnthalpyReference
from h2physics.adapters.lh2dt_valve_actuator import StrokeActuator
from h2physics.adapters.lh2dt_vent import VentEnvelope
from h2physics.adapters.underground_storage import _integrate_withdrawal
from h2physics.adsorption import AdsorptionBasis, AdsorptionState, loading_working_capacity
from h2physics.core import PropertyBasis
from h2physics.dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
from h2physics.mixtures import GasComposition
from h2physics.storage.hydride import ArrheniusRate, HydrideKinetics, VanthoffPlateau
from h2physics.storage.porous_reservoir import PorousReservoirGeometry
from h2physics.thermo.coolprop import CoolPropProperties

BASIS = PropertyBasis("Hydrogen", "authored-accounting-only")


def _mixture_trace_component():
    mixture = GasComposition("trace", ("H2", "N2"), (1.e-150, 1.), (.002, .028))
    masses = mixture.component_mass_flows(1.e150)
    assert masses[0] == pytest.approx(1./14., rel=2.e-14, abs=0.)
    assert math.isfinite(masses[1])


def _spin_mass_scales():
    reference = SpinEnthalpyReference(.25, 10000., "authored-reference")
    for mass in (0., 1.e-150, 1.e150):
        value = reference.enthalpy_j(mass, 1., 700000.)
        assert value == pytest.approx(-515000.*mass, rel=2.e-14, abs=0.)
        assert math.isfinite(value)


def _pure_quality_edges():
    properties = CoolPropProperties("Hydrogen")
    for quality in (0., 1.):
        state = properties.saturated(2.e5, quality)
        assert state.vapor_mass_fraction == quality
        assert math.isfinite(state.enthalpy_j_kg)
    # This tests host quality mapping/finite field retention, not native EOS.


def _darcy_extremes():
    with pytest.raises(ValueError, match="driving_pressure_pa must be positive"):
        solve_darcy_flow(DarcyGeometry(2., .002, 0.), density_kg_m3=1.2,
            viscosity_pa_s=2.e-5, driving_pressure_pa=0., friction_law=lambda re, rough: 64./re)
    for drive in (1.e-10, 1.e8):
        result = solve_darcy_flow(DarcyGeometry(2., .002, 0.), density_kg_m3=1.2,
            viscosity_pa_s=2.e-5, driving_pressure_pa=drive,
            friction_law=lambda re, rough: 64./re)
        expected = 1.2*math.pi*.002**4*drive/(128.*2.e-5*2.)
        assert result.mass_flow_kg_s == pytest.approx(expected, rel=2.e-8, abs=0.)
        assert math.isfinite(result.mass_flow_kg_s)


def _actuator_limits(actuator):
    assert actuator.advance(.25, 1., 0.) == .25
    assert actuator.advance(.25, 1., 1.e150) == 1.
    assert actuator.advance(.75, 0., 1.e150) == 0.


def _vaporizer_scales():
    cls = nominal._native_state_type("dynamic_vaporizer", "DynamicVaporizerState")
    for scale in (1.e-100, 1.e100):
        result = lumped_inventory_reader(scale, BASIS)(cls(scale, 3.*scale, 300.))
        assert result.total_energy_j == pytest.approx(303.*scale, rel=2.e-14, abs=0.)


def _tank_trace_vapor():
    cls = nominal._native_state_type("stratified_tank", "StratifiedTankState")
    result = stratified_inventory_reader(1.e-100, 1.e-100, BASIS)(
        cls(1., 10., 1.e-150, 2.e-150, 20., 25.))
    assert result.mass_kg == 1.
    assert result.fluid_internal_energy_j == 10.
    assert result.solid_internal_energy_j == pytest.approx(45.e-100, rel=2.e-14, abs=0.)


def _wall_cancelled_energy():
    cls = nominal._native_state_type("layered_tank", "LayeredTankState")
    result = layered_inventory_reader(rigid_volume_m3=1., wall_heat_capacities_j_k=(1.e-100,),
        basis=BASIS)(cls(2.e5, (1.,), (1.e5,), (1.,), (1.e5,), (300.,)))
    assert result.fluid_internal_energy_j == 0.
    assert result.total_energy_j == pytest.approx(300.e-100, rel=2.e-14, abs=0.)


def _withdrawal_dynamic_range():
    for rule in ("trapezoid", "left_hold", "right_hold"):
        value = _integrate_withdrawal((1.e150, 1.e150), (1.e-150,), rule)
        assert value[0] == pytest.approx(1., rel=2.e-14, abs=0.)
    assert _integrate_withdrawal((0., 0.), (1.e150,), "trapezoid")[0] == 0.


def _adsorption_zero_swing():
    basis = AdsorptionBasis("authored", ("H2",), "mol/kg", "authored", "no-fit",
        ("urn:authored",), "absolute")
    state = AdsorptionState(basis, (1.e5,), 300., ((1.e150, 1.e-150),))
    assert loading_working_capacity(state, state)[0] == 0.


def _hydride_cold_and_endpoints():
    equilibrium = VanthoffPlateau(24000., 80., 1.e5)
    kinetics = HydrideKinetics(equilibrium, ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.))
    assert kinetics.fraction_rate_s_inv(1., 300., 2.e5) == 0.
    assert kinetics.fraction_rate_s_inv(0., 300., 0.) == 0.
    assert kinetics.fraction_rate_s_inv(.5, 300., 0.) == pytest.approx(-.01)


def _hydride_exp_underflow_rejection():
    # Positive finite input but equilibrium underflows: refuse a zero fugacity.
    with pytest.raises(ValueError, match="equilibrium fugacity"):
        VanthoffPlateau(24000., 80., 1.e5).fugacity_pa(.01, .5, "absorption")


def _reaction_zero_and_exhaustion():
    from h2physics.reactions import ChemicalSpecies, StoichiometricReaction

    reaction = StoichiometricReaction("two-H", (
        ChemicalSpecies("H2", {"H": 2}, .002, "gas"),
        ChemicalSpecies("H", {"H": 1}, .001, "gas")), (-1., 2.))
    for amount in (1.e-100, 1.e100):
        result = reaction.convert({"H2": amount}, amount)
        assert result.final_amounts["H2"] == 0.
        assert result.final_amounts["H"] == pytest.approx(2.*amount, rel=2.e-14, abs=0.)
        assert math.isfinite(result.mass_residual_kg)


def _porous_geometry_scales():
    for scale in (1.e-50, 1.e50):
        geometry = PorousReservoirGeometry((scale, 2.*scale), scale,
            (.5,), (1.e-12,), (300.,), "synthetic-geometric-scaling")
        assert geometry.pore_volume_m3[0] == pytest.approx(1.5*math.pi*scale**3,
            rel=2.e-14, abs=0.)


def _compressor_edge_gate():
    state = CoolPropProperties("Hydrogen").state_pt(1.e5, 300.)
    envelope = CompressorEnvelope(state.pressure_pa, 2.e5, state.temperature_k, 400., 1.e-150, 1.e150, "authored")
    envelope.require_state(state)
    for flow in (1.e-150, 1.e150):
        envelope.require_flow(flow)
    with pytest.raises(ValueError, match="Mass flow"):
        envelope.require_flow(np.nextafter(1.e-150, 0.))


def _vent_edge_gate():
    state = CoolPropProperties("Hydrogen").state_pt(1.e5, 300.)
    VentEnvelope(state.pressure_pa, 2.e5, state.temperature_k, 400., .1, .1, .3, "authored").require_state(state)
    with pytest.raises(ValueError, match="pressure"):
        VentEnvelope(np.nextafter(state.pressure_pa, math.inf), 2.e5, state.temperature_k, 400., .1, .1, .3,
            "authored").require_state(state)


def _large_inventory_cancellation():
    initial = ConservedInventory(BASIS, 1.e100, 1.e100, 1.e100)
    balance = InventoryBalance(initial, initial, 0., 0., 0., 0.)
    assert balance.mass_residual_kg == 0.
    assert balance.energy_residual_j == 0.
    assert balance.violations(InventoryTolerances()) == ()


def _hx_zero_temperature_difference():
    model = nominal.CounterflowHeatExchanger(
        nominal.CounterflowDefinition("hx", "hot", "cold", (1.e6,), "authored", "one-cell"),
        hot_state_ph=lambda p, h: nominal._TestTemperature(h/2000.),
        cold_state_ph=lambda p, h: nominal._TestTemperature(h/4000.),
        domain=nominal.CounterflowDomain(250., 500., 1., 2.e6, "analytic-reference"),
        equation_relative_tolerance=1.e-12)
    with pytest.raises(RuntimeError, match="heat flow is nonpositive"):
        model.solve(nominal.CounterflowBoundary(.1, .1, 600000., 1200000.,
            (1.e5, 1.e5), (1.e5, 1.e5), "equal-inlet-T"))
    boundary = nominal.CounterflowBoundary(.1, .1, 600002., 1200000.,
        (1.e5, 1.e5), (1.e5, 1.e5), "small-positive-temperature-gap")
    # A single huge-UA midpoint cell crosses the endpoint temperatures. Refuse
    # that discretization rather than return an inadmissible finite-cell state.
    with pytest.raises(RuntimeError, match="hot-side temperature is not above"):
        model.solve(boundary)
    resolved = nominal.CounterflowHeatExchanger(
        nominal.CounterflowDefinition("hx", "hot", "cold", (100.,), "authored", "one-cell"),
        hot_state_ph=lambda p, h: nominal._TestTemperature(h/2000.),
        cold_state_ph=lambda p, h: nominal._TestTemperature(h/4000.),
        domain=nominal.CounterflowDomain(250., 500., 1., 2.e6, "analytic-reference"),
        equation_relative_tolerance=1.e-12)
    result = resolved.solve(boundary)
    assert result.cell_heat_w[0] == pytest.approx(.1/1.375, rel=1.e-6, abs=0.)


def _reliquefier_mass_scaling():
    for mass in (1.e-100, 1.e100):
        result = nominal.benchmark_hydrogen_liquefaction(
            feed=nominal.HydrogenFlowState(100000., 1000., "zero", "feed"),
            liquid_product=nominal.HydrogenFlowState(20000., 500., "zero", "product"),
            feed_mass_kg=mass, product_mass_kg=mass, external_work_j=200000.*mass,
            environment_temperature_k=300., process_window_id="window", process_evidence_id="authored")
        assert result.reversible_work_fraction == pytest.approx(.35, rel=2.e-14, abs=0.)
        assert result.specific_external_work_kwh_kg == pytest.approx(1./18., rel=2.e-14, abs=0.)


def _cryo_inventory_floor():
    from h2physics.adapters.cryo_compressed import CryoCompressedDomain

    state = CoolPropProperties("Hydrogen").state_pt(20.e6, 25.)
    domain = CryoCompressedDomain(state.temperature_k, 350., state.pressure_pa,
        120.e6, 1.e-12, 80., 2., (state.phase,), "authored")
    domain.require(state, np.nextafter(1.e-12, math.inf), state.temperature_k)
    with pytest.raises(ValueError, match="inventory domain"):
        domain.require(state, 1.e-12)


def _hydride_vessel_small_volume():
    from h2physics.storage.hydride_compressor import FiniteHydrideGasVessel, HydrideCompressorNative

    nominal._native_state_type("tank", "TankState")
    native = HydrideCompressorNative.from_installed(source_id="reviewed-LH2DT")
    gas = nominal.HydrideGasThermodynamics.coolprop("Hydrogen")
    observed = []
    state_pt = gas.state_pt

    def retain(p, t):
        point = state_pt(p, t)
        observed.append(point)
        return point

    gas = replace(gas, state_pt=retain)
    for volume in (1.e-12, 1.e6):
        vessel = FiniteHydrideGasVessel.coolprop(native, gas, vessel_id="supply",
            native_geometry=native.tank.TankGeometry(volume, 200., 2., 20.),
            pressure_pa=2.e6, temperature_k=300., wall_temperature_k=310.,
            minimum_gas_mass_kg=1.e-20, source_id="authored")
        assert vessel.initial_native_state.hydrogen_mass_kg == pytest.approx(
            volume*observed[-1].density_kg_m3, rel=2.e-14, abs=0.)


def _microsphere_floor():
    gas = nominal.HydrideGasThermodynamics.coolprop("Hydrogen")
    owner = nominal.MicrosphereStorage(inner_radius_m=.01, outer_radius_m=.011, cells=3,
        diffusivity_m2_s=lambda t: 1.e-12,
        solubility=nominal.PowerLawSolubility(nominal.HydrogenCarrier("molecular_hydrogen",
            gas.molar_mass_kg_mol), lambda t: 1.e-8, 1.), gas=gas,
        domain=nominal.MicrosphereDomain(250., 400., 1.e-12, 1.e8, 1.e-9),
        parameter_evidence="authored-floor")
    with pytest.raises(ValueError, match="inventory floor"):
        owner.gas_state(1.e-9, 300.)
    amount = np.nextafter(1.e-9, math.inf)
    state = owner.gas_state(amount, 300.)
    assert state.density_kg_m3 == pytest.approx(amount*gas.molar_mass_kg_mol/owner.cavity_volume_m3,
        rel=1.e-8, abs=0.)


def _two_phase_endpoint_gate():
    # Shared adapter's host admission rejects a finite zero pressure gradient;
    # finite quality endpoints themselves are actual native property inputs.
    from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe

    direct, low, bridge, _ = nominal._real_native_properties()
    native = nominal._native_state_type("pipe", "HEMPipe")(2., .002, 0., properties=low)
    adapter = Lh2dtDarcyPipe(native, bridge, viscosity_reader=lambda s: 1.e-5,
        friction_law=lambda re, rough: 64./re, friction_law_id="analytic",
        result_factory=nominal._native_state_type("pipe", "PipeResult"))
    state = low.from_ph(2.e5, direct.saturated(2.e5, 1.e-10).enthalpy_j_kg)
    result = adapter.evaluate(state, state)
    assert result.mass_flow_kg_s == 0.


def _solid_exhaustion():
    from h2physics.core import Origin

    species = (nominal.ChemicalSpecies("rich", {"Al": 1, "H": 2}, .029, "solid:authored"),
        nominal.ChemicalSpecies("spent", {"Al": 1}, .027, "solid:authored"),
        nominal.ChemicalSpecies("H2", {"H": 2}, .002, "gas:authored"))
    reaction = nominal.StoichiometricReaction("solid", species, (-1., 1., 1.))
    provider = nominal.FunctionalMolarEnthalpy(species,
        tuple(lambda t, p, cp=cp: cp*(t-300.) for cp in (30., 18., 12.)),
        "zero-formation", (200., 900.), (1.e4, 1.e6))
    kinetics = nominal.SolidReactionKinetics(reaction, lambda state, pars: 1.e100,
        "exhaustion-request", "authored-not-material", Origin.SYNTHETIC, {})
    evidence = nominal.SolidReactionEvidence("solid", "atoms", provider.basis_id,
        "common-T", "fixed-P", "no-takeoff", Origin.SYNTHETIC)
    owner = nominal.FiniteSolidReactionReactor(provider, kinetics, evidence,
        hydrogen_species="H2", mode="decomposition")
    result = owner.run(nominal.ThermochemicalInventory({"rich": 2.}, 300., 1.e5, provider.basis_id),
        (nominal.SolidReactionStep("one", 0., 1., "seconds", 0., (200., 900.), "authored",
            limit_policy="truncate"),))
    assert result.steps[0].accepted_extent_mol == 2.
    assert result.final.amounts_mol["rich"] == 0.
    assert result.final.temperature_k == pytest.approx(300.)


def _relief_saturated_travel():
    from h2physics.adapters.lh2dt import from_lh2dt_state
    from h2physics.adapters.lh2dt_relief import shared_native_relief
    from h2physics.adapters.relief_lift import (
        FiniteLiftRelief,
        PhasePickup,
        PhasePickupOwner,
        ReliefLiftLaw,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    direct, low, bridge, _ = nominal._real_native_properties()
    opening = NozzleOpening("relief", 1.e-12, 1., "authored")
    nozzle = HomogeneousIsentropicNozzle(direct)
    protection = shared_native_relief(native_valve_type=nominal._native_state_type("valve", "Valve"),
        native_relief_factory=nominal._native_state_type("valve", "PressureReliefValve"),
        result_factory=nominal._native_state_type("valve", "ValveResult"), nozzle=nozzle,
        bridge=bridge, opening=opening, set_pressure_pa_absolute=2.e5,
        reseat_pressure_pa_absolute=1.8e5, native_source_id="reviewed-LH2DT")
    point = low.from_pT(2.1e5, 300.)
    pickup = PhasePickupOwner("port", direct.basis, ("vapor",),
        lambda state: PhasePickup(state.pressure_Pa, from_lh2dt_state(state, basis=direct.basis),
            1., "vapor", "port", "accepted", state))
    model = FiniteLiftRelief(protection, nozzle=nozzle, opening=opening, pickup=pickup,
        law=ReliefLiftLaw(1.e150, 1.e150, .01, .05, "linear", "authored"), evidence_id="authored")
    downstream = direct.state_pt(1.e5, 300.)
    initial = model.initialize(time_s=0., clock_id="seconds", native_tank_state=point,
        downstream=downstream, initial_lift_fraction=0.)
    result = model.advance(initial, time_s=.05, native_tank_state=point, downstream=downstream)
    assert result.state.lift_fraction == 1.
    assert result.effective_opening_fraction == 1.


@dataclass(frozen=True)
class ExtremeCase:
    family: str
    target: str
    scenario: str
    scope: str
    check: object


CASES = (
    ExtremeCase("equipment.heat_exchanger", "CounterflowHeatExchanger.solve", "1e6UA with1mK gap and explicit zeroheat rejection", "model_numerics", _hx_zero_temperature_difference),
    ExtremeCase("equipment.reliquefier", "LiquefactionBenchmark properties", "1e±100batch preserves specific work and exergy ratio", "supporting_numerics", _reliquefier_mass_scaling),
    ExtremeCase("storage.cryo_compressed", "CryoCompressedDomain.require", "actual cryogenic state at domain edge and nextafter inventory floor", "host_domain_edge_only", _cryo_inventory_floor),
    ExtremeCase("storage.hydride_compressor", "FiniteHydrideGasVessel.coolprop extensive conversion", "1e-12and1e6volume at retained native point", "supporting_numerics", _hydride_vessel_small_volume),
    ExtremeCase("storage.microsphere", "MicrosphereStorage.gas_state", "inventory floor rejection and nextafter positive retained density", "host_domain_edge_only", _microsphere_floor),
    ExtremeCase("equipment.two_phase_pipe", "Lh2dtDarcyPipe.evaluate", "nearliquid endpoint equalpressure zero flow", "model_numerics", _two_phase_endpoint_gate),
    ExtremeCase("storage.solid_reaction", "FiniteSolidReactionReactor.run", "1e100rate request bounded by finite reactant inventory", "model_numerics", _solid_exhaustion),
    ExtremeCase("equipment.relief", "FiniteLiftRelief.advance", "1e150actuator rate clips to full lift without overflow", "model_numerics", _relief_saturated_travel),
    ExtremeCase("thermo.pure_fluid", "CoolPropProperties.saturated exposed quality", "both quality endpoints retained with finite fields", "host_field_mapping", _pure_quality_edges),
    ExtremeCase("thermo.mixtures", "GasComposition.component_mass_flows", "1e-150 trace fraction times1e150 mass retains nonzero component", "supporting_numerics", _mixture_trace_component),
    ExtremeCase("thermo.spin", "SpinEnthalpyReference.enthalpy_j", "zero and1e±150 mass with full para endpoint", "supporting_numerics", _spin_mass_scales),
    ExtremeCase("equipment.gas_pipe", "solve_darcy_flow", "zero1e-10and1e8 pressure drive with explicit analytic friction", "model_numerics", _darcy_extremes),
    ExtremeCase("equipment.valve", "StrokeActuator.advance", "zero duration and1e150duration saturation", "model_numerics", lambda: _actuator_limits(StrokeActuator("v", .2, .1, .1, "clock", "authored"))),
    ExtremeCase("equipment.pump", "PumpSpeedActuator.advance", "zero duration and1e150duration saturation", "model_numerics", lambda: _actuator_limits(PumpSpeedActuator("p", "clock", .2, .1, .2, "authored"))),
    ExtremeCase("equipment.vaporizer", "lumped_inventory_reader", "1e±100 inventory and wall capacity scaling", "supporting_numerics", _vaporizer_scales),
    ExtremeCase("equipment.lh2_tank", "stratified_inventory_reader", "trace1e-150 vapor and1e-100wall capacity", "supporting_numerics", _tank_trace_vapor),
    ExtremeCase("equipment.insulation", "layered_inventory_reader", "exact hPV cancellation plus tiny nonzero wall energy", "supporting_numerics", _wall_cancelled_energy),
    ExtremeCase("storage.underground", "_integrate_withdrawal", "1e150rate times1e-150duration and zero flow", "supporting_numerics", _withdrawal_dynamic_range),
    ExtremeCase("storage.adsorption", "loading_working_capacity", "equal loading with1e±150 site scales gives zero capacity", "supporting_numerics", _adsorption_zero_swing),
    ExtremeCase("storage.hydride_equilibrium", "VanthoffPlateau.fugacity_pa", "underflowing positive temperature refused as zero fugacity", "computed_domain_rejection", _hydride_exp_underflow_rejection),
    ExtremeCase("storage.hydride_dynamic", "HydrideKinetics.fraction_rate_s_inv", "fully charged/empty limits and vacuum desorption", "model_numerics", _hydride_cold_and_endpoints),
    ExtremeCase("storage.carrier_reaction", "StoichiometricReaction.convert", "complete reactant depletion at1e±100 inventory", "model_numerics", _reaction_zero_and_exhaustion),
    ExtremeCase("storage.porous_reservoir", "PorousReservoirGeometry.pore_volume_m3", "1e±50 radii/thickness cubed scaling", "supporting_numerics", _porous_geometry_scales),
    ExtremeCase("equipment.compressor", "CompressorEnvelope.require_flow/require_state", "accepted envelope endpoints and nextafter lower rejection", "host_domain_edge_only", _compressor_edge_gate),
    ExtremeCase("equipment.vent", "VentEnvelope.require_state", "actual gas exactly at pressure/T lower edge and nextafter rejection", "host_domain_edge_only", _vent_edge_gate),
    ExtremeCase("equipment.gas_tank", "InventoryBalance used by native tank host audit", "1e100stored mass/energy zero increment cancellation", "supporting_numerics", _large_inventory_cancellation),
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.family)
def test_selected_host_extreme(case, record_property):
    record_property("family", case.family)
    record_property("extreme_scenario", case.scenario)
    record_property("extreme_target", case.target)
    record_property("scope_kind", case.scope)
    case.check()
