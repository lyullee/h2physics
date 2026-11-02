"""Nominal independent numerical answers for selected host-owned calculations.

Analytical material/property closures below are explicitly test-only inputs;
they neither replace production CoolProp properties nor verify native engines.
"""

import importlib
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.counterflow_heat_exchanger import (
    CounterflowBoundary,
    CounterflowDefinition,
    CounterflowDomain,
    CounterflowHeatExchanger,
)
from h2physics.adapters.lh2dt_dynamics import lumped_inventory_reader, stratified_inventory_reader
from h2physics.adapters.lh2dt_insulation import layered_inventory_reader
from h2physics.adapters.lh2dt_pump_operation import (
    NormalizedPumpMap,
    PumpMapEvidence,
    PumpSpeedActuator,
)
from h2physics.adapters.lh2dt_spin import SpinEnthalpyReference
from h2physics.adapters.lh2dt_valve_actuator import StrokeActuator
from h2physics.adapters.liquefaction_performance import (
    HydrogenFlowState,
    benchmark_hydrogen_liquefaction,
)
from h2physics.adapters.underground_storage import _integrate_withdrawal
from h2physics.adsorption import AdsorptionBasis, AdsorptionState, loading_working_capacity
from h2physics.core import Origin, PropertyBasis
from h2physics.hydraulics import DarcyGeometry, solve_darcy_flow
from h2physics.materials.transport import HydrogenCarrier, PowerLawSolubility
from h2physics.mixtures import GasComposition
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction
from h2physics.storage.finite_hydride import HydrideGasThermodynamics
from h2physics.storage.hydride import (
    ArrheniusRate,
    HydrideBed,
    HydrideBoundary,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)
from h2physics.storage.microsphere import MicrosphereDomain, MicrosphereStorage
from h2physics.storage.porous_reservoir import (
    PorousReservoir,
    PorousReservoirGeometry,
    PorousReservoirSchedule,
)
from h2physics.storage.solid_reaction import (
    FiniteSolidReactionReactor,
    SolidReactionEvidence,
    SolidReactionKinetics,
    SolidReactionStep,
)
from h2physics.thermo.coolprop import CoolPropProperties
from h2physics.thermochemical import ThermochemicalInventory


def _native_state_type(module, symbol):
    folder = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
    if not (folder / "lh2dt/__init__.py").is_file():
        raise RuntimeError("Reviewed LH2DT initial-state dependency is unavailable")
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    return getattr(importlib.import_module("lh2dt." + module), symbol)


def _pure_state_identity():
    state = CoolPropProperties("Hydrogen").state_pt(2.e6, 310.)
    # Universal mass-specific identity checks the exposed field/unit mapping,
    # not the fitted native H2 EOS against an independent experiment.
    assert state.enthalpy_j_kg - state.internal_energy_j_kg == pytest.approx(
        state.pressure_pa / state.density_kg_m3, rel=1.e-12)


def _spin_reference_energy():
    reference = SpinEnthalpyReference(.25, 10000., "authored-common-spin-reference")
    # .2kg * (10000 + 700000*(.25-.65)) J/kg = -54000 J.
    assert reference.enthalpy_j(.2, .65, 700000.) == pytest.approx(-54000.)


def _vaporizer_inventory():
    # Actual native initial-state class; authored inputs are not solver outputs.
    state = _native_state_type("dynamic_vaporizer", "DynamicVaporizerState")(2., 30000., 300.)
    result = lumped_inventory_reader(100., PropertyBasis("Hydrogen", "authored-zero"))(state)
    assert result.solid_internal_energy_j == pytest.approx(30000.)
    assert result.total_energy_j == pytest.approx(60000.)


def _stratified_inventory():
    state = _native_state_type("stratified_tank", "StratifiedTankState")(
        2., 10000., .1, 2000., 20., 25.)
    result = stratified_inventory_reader(100., 200., PropertyBasis("Hydrogen", "authored-zero"))(state)
    assert result.mass_kg == pytest.approx(2.1)
    assert result.solid_internal_energy_j == pytest.approx(7000.)
    assert result.total_energy_j == pytest.approx(19000.)


def _layered_inventory():
    state = _native_state_type("layered_tank", "LayeredTankState")(
        1.e5, (1., .5), (100., 200.), (.1, .2), (500., 600.), (30., 40.))
    result = layered_inventory_reader(rigid_volume_m3=.001,
        wall_heat_capacities_j_k=(10., 20.), basis=PropertyBasis("Hydrogen", "authored-zero"))(state)
    # sum(m*h)=370 J; PV=100 J. Solid C*T sum=1100 J.
    assert result.fluid_internal_energy_j == pytest.approx(270.)
    assert result.solid_internal_energy_j == pytest.approx(1100.)
    assert result.total_energy_j == pytest.approx(1370.)


def _underground_rate_integral():
    # Host withdrawal quadrature only; no cavern model or native trace is made.
    np.testing.assert_allclose(_integrate_withdrawal((1., 3., 5.), (2., 3.), "trapezoid"),
                               (4., 12.), rtol=1.e-14)


def _mixture_amount_mass():
    mixture = GasComposition("authored-molar-algebra", ("H2", "N2"),
                             (.25, .75), (.002, .028))
    # For 4 mol: 1 mol H2 weighs .002 kg and 3 mol N2 weigh .084 kg.
    assert mixture.molar_mass_kg_mol == pytest.approx(.086 / 4.)
    np.testing.assert_allclose(mixture.mass_fractions, (1. / 43., 42. / 43.), rtol=1e-14)
    assert mixture.total_mass_flow_from_molar_flow(4.) == pytest.approx(.086)
    np.testing.assert_allclose(mixture.component_mass_flows(.086), (.002, .084), rtol=1e-14)


def _darcy_poiseuille():
    # Independently integrated laminar circular-tube flow, ordinary Re~2.5.
    result = solve_darcy_flow(DarcyGeometry(2., .002, 0.), density_kg_m3=1.2,
                             viscosity_pa_s=2.e-5, driving_pressure_pa=2.,
                             friction_law=lambda reynolds, _roughness: 64. / reynolds)
    expected = 1.2 * math.pi * .002**4 * 2. / (128. * 2.e-5 * 2.)
    assert result.mass_flow_kg_s == pytest.approx(expected, rel=1e-10)


def _valve_ramp():
    actuator = StrokeActuator("v", .2, .1, .1, "clock", "authored-ramp")
    # Opening: .1+.2*1.5=.4; closing: .7-.1*2=.5.
    assert actuator.advance(.1, .8, 1.5) == pytest.approx(.4)
    assert actuator.advance(.7, .2, 2.) == pytest.approx(.5)


def _pump_ramp_affinity():
    actuator = PumpSpeedActuator("p", "clock", .2, .1, .2, "authored-ramp")
    assert actuator.advance(.2, .8, 2.) == pytest.approx(.4)
    evidence = PumpMapEvidence("authored-map", "urn:authored:map", "authored",
                               "a" * 64, "normal-Hydrogen")
    model = NormalizedPumpMap("p-map", 3000., 2., 100000., 4., (0., 1.),
                              (1., .5), (.7, .8), (1., 2.), evidence)
    # Reduced Q=.5; interpolated head=.75, NPSH=1.5. Both scale as N^2=.25.
    actual = model.admit(speed_fraction=.5, mass_flow_kg_s=.5,
                        pressure_rise_pa=18750., npsh_required_m=1.5)
    np.testing.assert_allclose(actual[:3], (.5, 18750., 1.5), rtol=1e-14)


@dataclass(frozen=True)
class _TestTemperature:
    """Supported temperature-only test closure; no native object is imitated."""

    temperature_k: float


def _counterflow_one_cell():
    model = CounterflowHeatExchanger(
        CounterflowDefinition("hx", "hot", "cold", (100.,), "authored-UA", "one-cell"),
        hot_state_ph=lambda _p, h: _TestTemperature(h / 2000.),
        cold_state_ph=lambda _p, h: _TestTemperature(h / 4000.),
        domain=CounterflowDomain(250., 500., 1., 2.e6, "test-only-constant-cp"),
    )
    result = model.solve(CounterflowBoundary(.1, .1, 800000., 1200000.,
                                            (1.e5, 1.e5), (1.e5, 1.e5), "authored-inlets"))
    # Eliminate both outlet temperatures from the single-cell midpoint balance.
    expected = 10000. / 1.375
    assert result.cell_heat_w[0] == pytest.approx(expected, rel=1e-9)
    assert result.hot_temperature_k[-1] == pytest.approx(400. - expected / 200., rel=1e-10)
    assert result.cold_temperature_k[0] == pytest.approx(300. + expected / 400., rel=1e-10)


def _liquefaction_exergy():
    result = benchmark_hydrogen_liquefaction(
        feed=HydrogenFlowState(100000., 1000., "authored-common-zero", "feed"),
        liquid_product=HydrogenFlowState(20000., 500., "authored-common-zero", "liquid"),
        feed_mass_kg=2., product_mass_kg=2., external_work_j=400000.,
        environment_temperature_k=300., process_window_id="window", process_evidence_id="work",
    )
    # (20-100)kJ/kg - 300K*(.5-1)kJ/(kg K) = 70kJ/kg.
    assert result.minimum_reversible_work_j_kg == pytest.approx(70000.)
    assert result.minimum_reversible_work_j == pytest.approx(140000.)
    assert result.reversible_work_fraction == pytest.approx(.35)
    assert result.specific_external_work_kwh_kg == pytest.approx(1. / 18.)


def _adsorption_capacity():
    basis = AdsorptionBasis("authored", ("H2", "N2"), "mol/kg", "declared-input",
                            "no-fitted-isotherm", ("urn:authored:loading",), "absolute")
    charged = AdsorptionState(basis, (2.e5, 1.e5), 300., ((3., 2.), (1., 1.)))
    discharged = AdsorptionState(basis, (1.e5, .5e5), 300., ((1., .5), (.25, .5)))
    # Sum declared site amounts first: (5,2)-(1.5,.75)=(3.5,1.25) mol/kg.
    np.testing.assert_allclose(loading_working_capacity(charged, discharged), (3.5, 1.25))


def _hydride_plateau():
    model = VanthoffPlateau(24000., 80., 1.e5, 2., math.log(4.))
    # At 300 K, DeltaS-DeltaH/T=0; slope adds .5, absorption half-gap adds ln2.
    assert model.fugacity_pa(300., .75, "absorption") == pytest.approx(2.e5 * math.exp(.5))
    assert model.fugacity_pa(300., .75, "desorption") == pytest.approx(.5e5 * math.exp(.5))


def _hydride_closed_form():
    equilibrium = VanthoffPlateau(24000., 80., 1.e5)
    kinetics = HydrideKinetics(equilibrium, ArrheniusRate(.01, 0., 300.),
                              ArrheniusRate(.02, 0., 300.))
    bed = HydrideBed(HydrideParameters(.002, 1000., 0., .002, 0.), kinetics)
    times = np.array([0., 5., 10.])
    result = bed.simulate(times, HydrideState(.2, 300.),
                          lambda _t, _s: HydrideBoundary(2.e5, 300.))
    # x'=0.01*(1-x), x(0)=.2, so x=1-.8 exp(-.01t).
    np.testing.assert_allclose(result.fraction, 1. - .8 * np.exp(-.01 * times), atol=2.e-9)
    assert result.hydrogen_stored_kg[-1] == pytest.approx(.002 * (1. - .8 * math.exp(-.1)))


def _carrier_conversion():
    reaction = StoichiometricReaction("authored-MCH-dehydrogenation", (
        ChemicalSpecies("MCH", {"C": 7, "H": 14}, .098, "liquid"),
        ChemicalSpecies("toluene", {"C": 7, "H": 8}, .092, "liquid"),
        ChemicalSpecies("H2", {"H": 2}, .002, "gas")), (-1., 1., 3.))
    result = reaction.convert({"MCH": 2.}, .5)
    np.testing.assert_allclose(result.final_mol, (1.5, .5, 1.5))
    # One half mole conversion exports 3/2 mol H2 = .003kg on this declared basis.
    assert result.final_amounts["H2"] * .002 == pytest.approx(.003)


def _microsphere_amount_density():
    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    carrier = HydrogenCarrier("molecular_hydrogen", gas.molar_mass_kg_mol)
    owner = MicrosphereStorage(inner_radius_m=.01, outer_radius_m=.011, cells=3,
        diffusivity_m2_s=lambda _t: 1.e-12,
        solubility=PowerLawSolubility(carrier, lambda _t: 1.e-8, 1.), gas=gas,
        domain=MicrosphereDomain(250., 400., 1.e3, 1.e8, 1.e-9),
        parameter_evidence="authored-coordinate-conversion")
    result = owner.gas_state(.001, 300.)
    expected = .001 * gas.molar_mass_kg_mol / (4. * math.pi * .01**3 / 3.)
    assert result.density_kg_m3 == pytest.approx(expected, rel=1.e-9)


def _radial_darcy_reference():
    faces = (1., 2., 4., 8.)
    geometry = PorousReservoirGeometry(faces, 5., (.2, .2, .2),
        (1.e-12, 1.e-12, 1.e-12), (300., 300., 300.), "authored-radial-reference")
    # A supported, explicitly test-only incompressible property limit isolates
    # the host Darcy equation. No native engine or production H2 EOS is mocked.
    model = PorousReservoir(geometry=geometry, density_kg_m3=lambda _p, _t: 2.,
        viscosity_pa_s=lambda _p, _t: 1.e-5,
        property_evidence_id="analytical-verification-constant-rho-mu-only")
    centers = np.sqrt(np.array(faces[:-1]) * np.array(faces[1:]))
    initial = 2.e5 - 1.e5 * np.log(centers) / math.log(8.)
    schedule = PorousReservoirSchedule((0., 2.), initial, .5e5, 3.e5, None,
                                       "authored-clock", (2.e5, 2.e5))
    result = model.run(schedule, outer_pressure_pa=(1.e5, 1.e5))
    expected_rate = 2. * math.pi * 5. * 1.e-12 * 2. * 1.e5 / (1.e-5 * math.log(8.))
    assert result.cumulative_well_mass_kg[-1] == pytest.approx(2. * expected_rate, rel=2.e-7)
    assert result.cumulative_outer_boundary_mass_kg[-1] == pytest.approx(-2. * expected_rate, rel=2.e-7)


def _solid_frozen_rate_balance():
    species = (ChemicalSpecies("rich", {"Al": 1, "H": 2}, .029, "solid:authored"),
               ChemicalSpecies("spent", {"Al": 1}, .027, "solid:authored"),
               ChemicalSpecies("H2", {"H": 2}, .002, "gas:authored"))
    reaction = StoichiometricReaction("authored-solid", species, (-1., 1., 1.))
    # Explicit synthetic caloric closure isolates host finite-rate and thermal
    # balances; it is not a property correlation for an actual solid material.
    provider = FunctionalMolarEnthalpy(species,
        tuple(lambda t, p, cp=cp: cp * (t - 300.) for cp in (30., 18., 12.)),
        "authored-zero-formation", (200., 900.), (1.e4, 1.e6))
    kinetics = SolidReactionKinetics(reaction,
        lambda state, pars: pars["k"] * state.inventory.amounts_mol["rich"],
        "authored-first-order", "authored-no-material-data", Origin.SYNTHETIC, {"k": .1})
    evidence = SolidReactionEvidence("authored-solid", "balanced-atoms", provider.basis_id,
        "common-T", "fixed-P", "no-takeoff", Origin.SYNTHETIC)
    reactor = FiniteSolidReactionReactor(provider, kinetics, evidence,
        hydrogen_species="H2", mode="decomposition")
    result = reactor.run(ThermochemicalInventory({"rich": 2.}, 300., 1.e5, provider.basis_id),
        (SolidReactionStep("one", 0., 2., "seconds", 600., (200., 900.), "authored-command"),))
    # Frozen rate .1*2=.2mol/s for2s gives .4mol conversion. Total heat
    # capacity remains 2*30=60J/K, hence 600J raises common T by10K.
    assert result.steps[0].accepted_extent_mol == pytest.approx(.4)
    assert result.final.amounts_mol["rich"] == pytest.approx(1.6)
    assert result.hydrogen_generated_mol == pytest.approx(.4)
    assert result.final.temperature_k == pytest.approx(310.)


def _real_native_properties():
    from h2physics.adapters.lh2dt import Lh2dtProperties
    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    state_type = _native_state_type("properties", "ThermoState")
    direct = CoolPropProperties("Hydrogen")
    low = Lh2dtLowLevelProperties(direct, state_factory=state_type)
    return direct, low, Lh2dtProperties(low, reference_id=direct.basis.reference_id), state_type


def _two_phase_shared_darcy():
    from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
    direct, low, bridge, _ = _real_native_properties()
    left = low.from_ph(2.e5, direct.saturated(2.e5, .4).enthalpy_j_kg)
    right = low.from_ph(2.e5 - 10., left.specific_enthalpy_J_kg)
    native = _native_state_type("pipe", "HEMPipe")(2., .002, 0., properties=low,
        heat_into_fluid_W=3.)
    # Prescribed test viscosity isolates shared host hydraulics, not a
    # two-phase viscosity correlation or native equilibrium-property prediction.
    adapter = Lh2dtDarcyPipe(native, bridge, viscosity_reader=lambda _: 1.e-5,
        friction_law=lambda re, rough: 64. / re,
        friction_law_id="analytic-laminar-reference", result_factory=_native_state_type("pipe", "PipeResult"))
    result = adapter.evaluate(left, right)
    expected = left.density_kg_m3 * math.pi * .002**4 * 10. / (128. * 1.e-5 * 2.)
    assert result.mass_flow_kg_s == pytest.approx(expected)
    assert result.outlet_specific_enthalpy_J_kg - left.specific_enthalpy_J_kg == pytest.approx(3. / expected)


def _hydride_vessel_initial_accounting():
    from h2physics.storage.hydride_compressor import FiniteHydrideGasVessel, HydrideCompressorNative
    _native_state_type("tank", "TankState")
    native = HydrideCompressorNative.from_installed(source_id="reviewed-installed-LH2DT")
    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    observed = []
    actual_state_pt = gas.state_pt

    def retain_actual_point(pressure, temperature):
        point = actual_state_pt(pressure, temperature)
        observed.append(point)
        return point

    gas = replace(gas, state_pt=retain_actual_point)
    vessel = FiniteHydrideGasVessel.coolprop(native, gas, vessel_id="supply",
        native_geometry=native.tank.TankGeometry(.03, 200., 2., 20.),
        pressure_pa=2.e6, temperature_k=300., wall_temperature_k=310.,
        minimum_gas_mass_kg=1.e-8, source_id="authored-initial-inventory")
    # Actual single provider input is retained; check host extensive conversion,
    # without a second backend invocation masquerading as an independent EOS.
    assert len(observed) == 1
    state = observed[0]
    assert vessel.initial_native_state.hydrogen_mass_kg / state.density_kg_m3 == pytest.approx(.03)
    assert vessel.initial_native_state.hydrogen_internal_energy_J / state.internal_energy_j_kg == pytest.approx(
        .03 * state.density_kg_m3)


def _cryo_initial_accounting():
    from h2physics.adapters.cryo_compressed import (
        CryoCompressedDomain,
        CryoCompressedEvidence,
        CryoCompressedGeometry,
        CryoCompressedNative,
        CryoCompressedStorage,
    )
    from h2physics.release import NozzleOpening
    _native_state_type("tank", "TankState")
    owner = CryoCompressedStorage(CryoCompressedNative.from_installed(source_id="reviewed-LH2DT"),
        properties=CoolPropProperties("Hydrogen"), geometry=CryoCompressedGeometry(.01, 100., 1., 10.),
        domain=CryoCompressedDomain(20., 350., 2.e6, 120.e6, .01, 80., 2.,
            ("supercritical_liquid", "supercritical", "supercritical_gas"), "authored-envelope"),
        evidence=CryoCompressedEvidence("initial", "geometry", "heat", "protection", "no-solid", Origin.SYNTHETIC),
        initial_pressure_pa_absolute=20.e6, initial_temperature_k=25., initial_wall_temperature_k=25.,
        opening=NozzleOpening("opening", 1.e-8, 1., "area"),
        set_pressure_pa_absolute=100.e6, reseat_pressure_pa_absolute=99.e6)
    fluid, state = owner.initial_fluid, owner.initial_native_state
    assert state.hydrogen_mass_kg / fluid.density_kg_m3 == pytest.approx(.01)
    assert state.hydrogen_internal_energy_J == pytest.approx(.01 * fluid.density_kg_m3 * fluid.internal_energy_j_kg)


def _compressor_host_energy():
    from h2physics.adapters.lh2dt_compressor import CompressorEnvelope, Lh2dtCompressorStage
    direct, low, bridge, state_type = _real_native_properties()
    native = _native_state_type("compressor", "Compressor")(low, pressure_ratio=2., isentropic_efficiency=.75)
    stage = Lh2dtCompressorStage(native, bridge, state_factory=state_type, stage_id="stage",
        envelope=CompressorEnvelope(1.e4, 100.e6, 80., 1800., 1.e-5, 1., "authored-envelope"))
    result = stage.evaluate(direct.state_pt(1.e5, 300.), .03)
    # Native temperatures/work are inputs to this host accounting check.
    # Compare the independently assembled signed first-law total, not native EOS.
    assert result.transfer.inlet_enthalpy_flow_w == pytest.approx(.03 * result.inlet.enthalpy_j_kg)
    assert result.transfer.outlet_enthalpy_flow_w == pytest.approx(.03 * result.outlet.enthalpy_j_kg)
    expected = .03 * (result.outlet.enthalpy_j_kg - result.inlet.enthalpy_j_kg) - result.power.shaft_work_w
    assert result.energy_residual_w == pytest.approx(expected, abs=1.e-8)
    assert result.transfer.outlet_enthalpy_flow_w > result.transfer.inlet_enthalpy_flow_w




def _gas_tank_host_ledger():
    from h2physics.adapters.lh2dt_relief import (
        Lh2dtReliefTankDriver,
        ReliefTankBoundary,
        shared_native_relief,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    direct, low, bridge, state_type = _real_native_properties()
    opening = NozzleOpening("sealed-reference", 1.e-8, 1., "authored")
    protection = shared_native_relief(native_valve_type=_native_state_type("valve", "Valve"),
        native_relief_factory=_native_state_type("valve", "PressureReliefValve"),
        result_factory=_native_state_type("valve", "ValveResult"),
        nozzle=HomogeneousIsentropicNozzle(direct), bridge=bridge, opening=opening,
        set_pressure_pa_absolute=1.e7, reseat_pressure_pa_absolute=9.e6,
        native_source_id="reviewed-LH2DT")
    geometry = _native_state_type("tank", "TankGeometry")(.01, 100., 1., 10.)
    tank = _native_state_type("tank", "HomogeneousTank")(geometry, low)
    point = low.from_pT(2.e5, 300.)
    mass = .01*point.density_kg_m3
    initial = _native_state_type("tank", "TankState")(mass,
        mass*point.specific_internal_energy_J_kg, 300.)
    boundary = ReliefTankBoundary("seconds", 0., 1., direct.state_pt(1.e5, 300.),
        lambda t: 300., lambda t, state, wall: 100.-(300.-wall), "constant-net100W")
    driver = Lh2dtReliefTankDriver(tank, protection,
        flow_factory=_native_state_type("streams", "MassEnergyFlow"), state_factory=state_type)
    trace = driver.run(initial, duration_s=1., maximum_step_s=.1, start_time_s=0.,
        clock_id="seconds", boundary=boundary, minimum_inventory_kg=1.e-8)
    # Host cumulative source/heat bookkeeping, with actual native intervals as
    # inputs: no independent native tank-temperature or EOS prediction asserted.
    assert trace.external_heat_j[-1] == pytest.approx(100., abs=1.e-8)
    assert trace.released_mass_kg[-1] == pytest.approx(0., abs=1.e-15)
    assert trace.energy_residual_j[-1] == pytest.approx(0., abs=1.e-6)


def _relief_lift_rate():
    from h2physics.adapters.lh2dt import from_lh2dt_state
    from h2physics.adapters.lh2dt_relief import shared_native_relief
    from h2physics.adapters.relief_lift import (
        FiniteLiftRelief,
        PhasePickup,
        PhasePickupOwner,
        ReliefLiftLaw,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    direct, low, bridge, _ = _real_native_properties()
    opening = NozzleOpening("relief", 1.e-8, 1., "authored-area")
    nozzle = HomogeneousIsentropicNozzle(direct)
    protection = shared_native_relief(native_valve_type=_native_state_type("valve", "Valve"),
        native_relief_factory=_native_state_type("valve", "PressureReliefValve"),
        result_factory=_native_state_type("valve", "ValveResult"), nozzle=nozzle, bridge=bridge,
        opening=opening, set_pressure_pa_absolute=2.e5, reseat_pressure_pa_absolute=1.8e5,
        native_source_id="reviewed-LH2DT")
    point = low.from_pT(2.1e5, 300.)
    pickup = PhasePickupOwner("authored-port", direct.basis, ("vapor",),
        lambda state: PhasePickup(state.pressure_Pa, from_lh2dt_state(state, basis=direct.basis),
            1., "vapor", "authored-port", "accepted-point", state))
    model = FiniteLiftRelief(protection, nozzle=nozzle, opening=opening, pickup=pickup,
        law=ReliefLiftLaw(4., 2., .01, .05, "linear", "authored"), evidence_id="reference")
    downstream = direct.state_pt(1.e5, 300.)
    initial = model.initialize(time_s=0., clock_id="seconds", native_tank_state=point,
        downstream=downstream, initial_lift_fraction=.1)
    result = model.advance(initial, time_s=.05, native_tank_state=point, downstream=downstream)
    # Exact host travel: .1+4*.05=.3; leakage plus open-seat area=.01+.99*.3.
    assert result.state.lift_fraction == pytest.approx(.3)
    assert result.effective_opening_fraction == pytest.approx(.307)


def _vent_host_accounting():
    from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
    from h2physics.adapters.lh2dt_vent import Lh2dtVentStack, VentEnvelope
    direct, low, bridge, state_type = _real_native_properties()
    native = _native_state_type("vent_stack", "VentStack")(2., .002, 0.,
        properties=low, ambient_temperature_K=310., ambient_UA_W_K=0.)
    pipe = Lh2dtDarcyPipe(native.pipe, bridge, viscosity_reader=lambda _: 1.e-5,
        friction_law=lambda re, rough: 64./re, friction_law_id="laminar-reference",
        result_factory=_native_state_type("pipe", "PipeResult"))
    adapter = Lh2dtVentStack(native, bridge, state_factory=state_type,
        envelope=VentEnvelope(1.e4, 1.e7, 80., 1000., .1, .1, .3, "reference"),
        component_id="vent", evidence_id="authored", allow_reverse=False,
        viscosity_reader=lambda _: 1.e-5, sound_speed_reader=lambda state: direct.state_ph(state.pressure_Pa, state.specific_enthalpy_J_kg).speed_of_sound_m_s,
        sound_speed_capability_id="actual-native", hydraulic_pipe=pipe)
    left, right = direct.state_pt(2.e5, 300.), direct.state_pt(2.e5-10., 300.)
    result = adapter.evaluate(left, right, left_node="left", right_node="right",
        left_port_id="out", right_port_id="in")
    expected_mass = left.density_kg_m3 * math.pi * .002**4 * 10. / (128.*1.e-5*2.)
    assert result.transfer.mass_flow_kg_s == pytest.approx(expected_mass)
    velocity = expected_mass / (left.density_kg_m3 * math.pi * .002**2/4.)
    assert result.upstream_hydraulic_kinetic_energy_j_kg == pytest.approx(velocity**2/2.)
    assert result.transfer.inlet_enthalpy_flow_w == pytest.approx(expected_mass*left.enthalpy_j_kg)


@dataclass(frozen=True)
class FormulaCase:
    family: str
    target: str
    scope: str
    oracle: str
    check: Callable


CASES = (
    FormulaCase("equipment.gas_tank", "Lh2dtReliefTankDriver host cumulative ledger", "supporting_geometry_or_accounting",
        "constant net100W for1s gives cumulative100J, zero closed relief mass", _gas_tank_host_ledger),
    FormulaCase("equipment.relief", "FiniteLiftRelief.advance", "model_equation",
        "exact linear lift .1+4*.05=.3 and leakage area .01+.99*.3=.307", _relief_lift_rate),
    FormulaCase("equipment.vent", "Lh2dtVentStack.evaluate host hydraulics/accounting", "supporting_geometry_or_accounting",
        "Poiseuille rate, v squared/2 and mdot*h on actual native gas input", _vent_host_accounting),
    FormulaCase("equipment.two_phase_pipe", "Lh2dtDarcyPipe.evaluate", "supporting_geometry_or_accounting",
        "actual wet-state density plus Poiseuille mass rate and heat/mdot enthalpy increment", _two_phase_shared_darcy),
    FormulaCase("equipment.compressor", "ConnectionTransfer enthalpy-flow and residual accounting",
        "supporting_geometry_or_accounting", "actual native states: mdot*h and mdot*(hout-hin)-W", _compressor_host_energy),
    FormulaCase("storage.cryo_compressed", "CryoCompressedStorage initial extensive conversion",
        "supporting_geometry_or_accounting", "retained actual fluid point: mass/rho=.01m3 and U=rho*V*u", _cryo_initial_accounting),
    FormulaCase("storage.hydride_compressor", "FiniteHydrideGasVessel.coolprop extensive conversion",
        "supporting_geometry_or_accounting", "actual fluid point: mass/rho=.03m3 and U=mass*u", _hydride_vessel_initial_accounting),
    FormulaCase("storage.solid_reaction", "FiniteSolidReactionReactor.run", "model_equation",
        "frozen rate .1*2mol*2s=.4mol;600J/(60J/K)=10K", _solid_frozen_rate_balance),
    FormulaCase("thermo.pure_fluid", "CoolPropProperties.state_pt exposed fields",
        "supporting_geometry_or_accounting", "mass-specific identity h-u=P/rho; not EOS accuracy",
        _pure_state_identity),
    FormulaCase("thermo.spin", "SpinEnthalpyReference.enthalpy_j",
        "supporting_geometry_or_accounting", ".2*(10000+700000*(.25-.65))=-54000J",
        _spin_reference_energy),
    FormulaCase("thermo.mixtures", "GasComposition mass/mole conversions",
        "supporting_geometry_or_accounting", "4mol mixture masses .002kg H2+.084kg N2", _mixture_amount_mass),
    FormulaCase("equipment.gas_pipe", "solve_darcy_flow", "model_equation",
        "Poiseuille mdot=rho*pi*D^4*dP/(128muL)", _darcy_poiseuille),
    FormulaCase("equipment.valve", "StrokeActuator.advance", "model_equation",
        "specified linear stroke-rate integration", _valve_ramp),
    FormulaCase("equipment.pump", "NormalizedPumpMap.admit/PumpSpeedActuator.advance", "model_equation",
        "linear ramp and Q/N map coordinate, head and NPSH scale N^2", _pump_ramp_affinity),
    FormulaCase("equipment.heat_exchanger", "CounterflowHeatExchanger.solve", "model_equation",
        "independent one-cell midpoint heat balance closed form Q=10000/1.375W", _counterflow_one_cell),
    FormulaCase("equipment.vaporizer", "lumped_inventory_reader",
        "supporting_geometry_or_accounting", "wall C*T=30000J, total U=60000J; authored native initial state",
        _vaporizer_inventory),
    FormulaCase("equipment.lh2_tank", "stratified_inventory_reader",
        "supporting_geometry_or_accounting", "two-region mass2.1kg; wall7000J plus fluid12000J",
        _stratified_inventory),
    FormulaCase("equipment.insulation", "layered_inventory_reader",
        "supporting_geometry_or_accounting", "sum(m*h)-P*V=270J and sum(C*T)=1100J",
        _layered_inventory),
    FormulaCase("equipment.reliquefier", "LiquefactionBenchmark exergy/work properties",
        "supporting_geometry_or_accounting", "(dh-T0*ds)=70000J/kg and J->kWh", _liquefaction_exergy),
    FormulaCase("storage.adsorption", "loading_working_capacity", "supporting_geometry_or_accounting",
        "site-summed charged-minus-discharged loading=(3.5,1.25)mol/kg", _adsorption_capacity),
    FormulaCase("storage.hydride_equilibrium", "VanthoffPlateau.fugacity_pa", "model_equation",
        "DeltaS-DeltaH/T=0 plus independent slope and half-log-gap exponent", _hydride_plateau),
    FormulaCase("storage.hydride_dynamic", "HydrideBed.simulate", "model_equation",
        "exact nonzero uptake x(t)=1-.8exp(-.01t)", _hydride_closed_form),
    FormulaCase("storage.carrier_reaction", "StoichiometricReaction.convert", "model_equation",
        "MCH->toluene+3H2 extent .5mol yields1.5molH2", _carrier_conversion),
    FormulaCase("storage.microsphere", "MicrosphereStorage.gas_state", "supporting_geometry_or_accounting",
        "rho=n*M/(4pi*r^3/3), native EOS prediction not independently checked", _microsphere_amount_density),
    FormulaCase("storage.porous_reservoir", "PorousReservoir.run", "model_equation",
        "steady nonzero radial Darcy rate2pi*L*k*rho*dP/(mu*ln(rout/rin))", _radial_darcy_reference),
    FormulaCase("storage.underground", "_integrate_withdrawal",
        "supporting_geometry_or_accounting", "linear-rate trapezoids1to3 over2s=4kg,3to5 over3s=12kg",
        _underground_rate_integral),
)

FORMULA_FAMILY_IDS = tuple(case.family for case in CASES)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.family)
def test_independent_nominal_formula(case, record_property):
    record_property("family", case.family)
    record_property("formula_target", case.target)
    record_property("oracle_description", case.oracle)
    record_property("formula_scope", case.scope)
    record_property("oracle_kind", "identity_check" if case.family == "thermo.pure_fluid" else "independent_known_answer")
    case.check()
