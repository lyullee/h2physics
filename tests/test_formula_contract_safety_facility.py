"""Nominal independent answers for project-owned safety calculations.

Native prediction engines are not replaced or independently qualified here.
Several checks intentionally concern only a named geometry/accounting formula.
"""

import importlib
import math
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pytest

from h2physics.core import Origin, PropertyBasis, ThermoState

FORMULA_FAMILY_IDS = (
    "release.gas", "release.liquid", "release.near_field", "release.droplets",
    "surface.pool", "dispersion.buoyant_layer", "dispersion.compartment_network",
    "combustion.piston_engine", "combustion.gas_turbine", "combustion.overpressure",
    "effects.fragment_trajectory", "effects.cryogenic", "facility.network",
    "facility.monitoring", "facility.detector_reliability", "facility.isolation",
    "release.impact", "effects.exposure", "dispersion.obstacle",
    "release.two_phase", "combustion.pool_fire", "combustion.flash_fire", "combustion.jet_fire",
)


class _ConstantCpGasReference:
    """Explicit analytic verification medium, never a production fallback."""

    basis = PropertyBasis("analytic-gas", "authored-constant-cp-reference")
    gas_constant = 4000.
    gamma = 1.4
    cp = 14000.

    def state_pt(self, pressure, temperature):
        rho = pressure / (self.gas_constant * temperature)
        h = self.cp * temperature
        s = self.cp * math.log(temperature / 300.) - self.gas_constant * math.log(pressure / 1.e5)
        return ThermoState(self.basis, pressure, temperature, rho, h,
                           h - pressure / rho, s, "gas")

    def state_ps(self, pressure, entropy):
        temperature = 300. * math.exp((entropy + self.gas_constant * math.log(pressure / 1.e5)) / self.cp)
        return self.state_pt(pressure, temperature)


class _IncompressibleReference:
    """Analytic constant-density liquid for verification of the nozzle kernel."""

    basis = PropertyBasis("analytic-liquid", "authored-incompressible-reference")
    density = 80.

    def state_ps(self, pressure, _entropy):
        return ThermoState(self.basis, pressure, 30., self.density,
                           10000. + pressure / self.density, 10000., 0., "liquid")


def _gas_nozzle():
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    properties = _ConstantCpGasReference()
    p0, temperature = 5.e6, 300.
    opening = NozzleOpening.circular("verification-hole", .002,
                                     effective_area_factor=.8, area_basis_id="authored-area")
    result = HomogeneousIsentropicNozzle(properties).solve(
        properties.state_pt(p0, temperature), back_pressure_pa=1.e6, opening=opening)
    # Independently integrated ideal isentropic momentum/energy balance.
    gamma = 1.4
    expected_flux = p0 * math.sqrt(gamma / (4000. * temperature)) * (
        2. / (gamma + 1.)) ** ((gamma + 1.) / (2. * (gamma - 1.)))
    expected_mass = expected_flux * .8 * math.pi * .002**2 / 4.
    assert result.mass_flow_kg_s == pytest.approx(expected_mass, rel=2.e-8)


def _liquid_nozzle():
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    properties = _IncompressibleReference()
    opening = NozzleOpening.circular("verification-hole", .002,
                                     effective_area_factor=.75, area_basis_id="authored-area")
    result = HomogeneousIsentropicNozzle(properties).solve(
        properties.state_ps(8.e5, 0.), back_pressure_pa=2.e5, opening=opening)
    # Bernoulli's independent incompressible discharge answer.
    expected = .75 * math.pi * .002**2 / 4. * math.sqrt(2. * 80. * 6.e5)
    assert result.mass_flow_kg_s == pytest.approx(expected, rel=2.e-8)


def _jet_coordinates():
    from h2physics.adapters.degali import JetPlane
    from h2physics.release import SourceLocation

    plane = JetPlane("xyz", (1., 2., 3.), (0., 1., 0.), (0., 0., 1.))
    source = SourceLocation("jet", "clock", "xyz", (1., 5., 7.), (0., .6, .8))
    assert plane.project(source) == pytest.approx((3., 4., math.atan2(4., 3.)), abs=1.e-13)


def _parcel_evaporation():
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
    )
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    boundary = ParcelBoundary("clock", "xyz", "declared-carrier", 1.2, 1.8e-5,
        (0., 0., 0.), (0., 0., -9.81), 1.e5, 100., .002, .01)
    flight = SaturatedParcelFlight(properties, 1.e5, boundary,
        lambda _state: BoilingHeat(1., "authored-constant-one-watt"),
        force_approximation_evidence_id="isolated-heavy-sphere")
    result = flight.run(start_s=0., end_s=.1, position_m=(0., 0., 10.),
        velocity_m_s=(0., 0., 0.), mass_kg=1.e-4, residual_mass_floor_kg=1.e-5,
        maximum_step_s=.02, relative_tolerance=1.e-9, absolute_tolerances=(1.e-10,) * 17)
    # The host evaporation equation dm/dt=-Q/L has a linear exact solution.
    latent = flight.vapor.enthalpy_j_kg - flight.liquid.enthalpy_j_kg
    expected_evaporated = .1 / latent
    assert result.evaporated_mass_kg == pytest.approx(expected_evaporated, rel=1.e-8, abs=1.e-14)
    assert result.states[-1].mass_kg == pytest.approx(1.e-4 - expected_evaporated, abs=1.e-12)


def _pool_inflow_integral():
    from h2physics.adapters.pool import DeclaredGroundInflow
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    target = Path(__file__).resolve().parents[1] / "artifacts/native_pool_packages"
    if not (target / "dynamiclh2poolx/inflow.py").is_file():
        raise RuntimeError("The declared native pool input dependency is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    cls = importlib.import_module("dynamiclh2poolx.inflow").DeclaredInflow
    native = cls((0., 2.), (.01, .02))
    state = CoolPropProperties("Hydrogen").saturated(1.e5, 0.)
    inflow = DeclaredGroundInflow(native,
        SourceLocation("pool", "clock", "xyz", (0., 0., 0.), (1., 0., 0.)),
        state, 10., 15., Origin.SYNTHETIC, "authored-step-input", "window_end")
    assert inflow.cumulative_mass_kg(15., clock_id="clock") == pytest.approx(.08)


def _plume_coefficient():
    from h2physics.buoyant_layer import _plume_coefficient

    coefficient = _plume_coefficient(.1)
    # Cubing the similarity coefficient eliminates the implementation's cube root.
    assert coefficient**3 == pytest.approx(1.92 * .1**2 / math.pi**2, rel=2.e-14)


def _compartment_mixing():
    from h2physics.compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkModel,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )

    room = WellMixedCompartment("room", 1., 101325., 300., .02, "state", "state-data")
    feed = CompartmentMolarTransfer("feed", None, "room", (1.,), "feed", "feed-data", "clock", .2)
    exhaust = CompartmentMolarTransfer("exhaust", "room", None, (1.,), "out", "out-data", "clock")
    result = simulate_hydrogen_compartment_network(
        CompartmentNetworkModel((room,), (feed, exhaust), "clock"), time_samples_s=(0., 3.))
    # Fixed-stock stirred-room ODE: dx/dt=(F/n)(x_in-x).
    n = 101325. / (8.31446261815324 * 300.)
    expected = .2 + (.02 - .2) * math.exp(-3. / n)
    assert result.hydrogen_mole_fraction[-1, 0] == pytest.approx(expected, rel=2.e-12)


def _piston_geometry():
    from h2physics.combustion.closed_charge_engine import SliderCrank

    geometry = SliderCrank(.08, .08, .15, 10., 1500.)
    area = math.pi * .08**2 / 4.
    clearance = area * .08 / 9.
    # A right-angle crank has displacement r+l-sqrt(l*l-r*r).
    expected = clearance + area * (.04 + .15 - math.sqrt(.15**2 - .04**2))
    assert geometry.volume_m3(math.pi / 2.) == pytest.approx(expected, rel=2.e-14)
    expected_rate = area * .04 * (1500. * 2. * math.pi / 60.)
    assert geometry.volume_rate_m3_s(math.pi / 2.) == pytest.approx(expected_rate, rel=2.e-14)


def _engine_stream_integral():
    from h2physics.combustion.closed_charge_engine import EngineBoundarySchedule
    from h2physics.combustion.engine_boundary_ledger import (
        EngineBoundaryStream,
        integrate_engine_boundary_streams,
    )

    mass = EngineBoundarySchedule("mass_flow", "kg/s", "feed", 0., (0., 2.), (1., 3.))
    heat = EngineBoundarySchedule("specific_enthalpy", "J/kg", "feed-h", 0., (0., 2.), (10., 14.))
    result = integrate_engine_boundary_streams(
        (EngineBoundaryStream("feed", "intake", mass, heat, "same-reference"),),
        start_time_s=0., end_time_s=2.)
    # Integral of (1+t)(10+2t) = 10+12t+2t² on [0,2].
    assert result.mass_into_cylinder_kg == pytest.approx(4.)
    assert result.enthalpy_into_cylinder_j == pytest.approx(148. / 3.)


def _shaft_energy():
    from h2physics.combustion.shaft_transient import ShaftTransientInputs, integrate_shaft_transient

    inputs = ShaftTransientInputs((0., 2.), (1000., 1000.), (400., 400.), (0., 0.),
        (0., 1., 2.), 2., 100., 50., 200., 0., 0., 1.e-10, 1.e-7, .2,
        "shaft", "gross-powers", "declared-load", "inertia")
    result = integrate_shaft_transient(inputs)
    # E0=10000 J; net600 W for2 s adds1200 J; omega=sqrt(2E/J).
    assert result.kinetic_energy_j[-1] == pytest.approx(11200., rel=1.e-12)
    assert result.speed_rad_s[-1] == pytest.approx(math.sqrt(11200.), rel=1.e-12)


def _participating_energy():
    from h2physics.adapters.hyram_overpressure import DetonableHydrogenEnergy

    result = DetonableHydrogenEnergy(.25, 120.e6, "mass", "heat", "LHV", "source", Origin.SYNTHETIC)
    assert result.energy_j == pytest.approx(30.e6)


def _quadratic_drag_fragment():
    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment,
        FragmentFlightSettings,
        FragmentLaunch,
        integrate_fragment_flight,
    )

    launch = FragmentLaunch("fragment", 2., 1., .5, (1., 2., 10.), (0., 0., -1.), 0., "xyz", "launch")
    env = FragmentFlightEnvironment(lambda _z: 1.2, lambda _p, _t: np.zeros(3),
        np.array((0., 0., -9.81)), "xyz", "environment", "density", "wind")
    result = integrate_fragment_flight(launch, env, FragmentFlightSettings("clock", np.array((0., .5))))
    # Downward-positive dv/dt=g-k*v²: exact tanh solution at positive g and drag.
    k = .5 * 1.2 * .5 * 1. / 2.
    terminal = math.sqrt(9.81 / k)
    initial_argument = math.atanh(1. / terminal)
    argument = initial_argument + 9.81 * .5 / terminal
    displacement = math.log(math.cosh(argument) / math.cosh(initial_argument)) / k
    assert result.position_m[-1] == pytest.approx((1., 2., 10. - displacement), abs=1.e-8)
    assert result.velocity_m_s[-1] == pytest.approx((0., 0., -terminal * math.tanh(argument)), abs=1.e-8)


def _oxygen_deficit():
    from h2physics.adapters.oxygen_threshold_integral import _integrate_positive_threshold_deficit

    # Deficit increases linearly .01->.03 over2 s: trapezoid area .04 fraction*s.
    actual = _integrate_positive_threshold_deficit((0., 2.), (.19, .17), .2)
    assert actual == pytest.approx((.04,), abs=1.e-15)


def _facility_continuity():
    from h2physics.facility_continuity import (
        ExternalFacilityRate,
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
        FacilityStorageRate,
    )

    basis = PropertyBasis("authored-fluid", "same-reference")
    state = ThermoState(basis, 1.e5, 300., 1., 120., -99880., 0., "gas")
    frame = FacilityContinuityFrame("clock", 1., (),
        (ExternalFacilityRate("in", "node", "port", .2, state, 7., 3.),),
        (FacilityStorageRate("node", basis, .15, 30.),))
    result = FacilityContinuityAudit((FacilityNode("node", basis),)).audit(frame, require_closed=False)
    # Material power=.2*120=24W, external heat+work=10W.
    assert result.mass_residual_kg_s == pytest.approx(-.05)
    assert result.node_energy_residual_w == pytest.approx(-4.)


def _sensor_step():
    from h2physics.adapters.gas_detection import (
        FirstOrderConcentrationSensorConfig,
        evaluate_first_order_concentration_sensor,
    )

    config = FirstOrderConcentrationSensorConfig("sensor", "roof", "clock", "H2-mole-fraction", "1",
        2., 5., "sensor", "tau", "first-order")
    result = evaluate_first_order_concentration_sensor(config, time_s=(0., 3.),
        true_concentration=(.1, .1), initial_indication=.02, source_evidence_id="step",
        operating_mode_id="nominal", episode_id="episode", origin=Origin.SYNTHETIC)
    assert result.indicated_concentration[-1] == pytest.approx(.1 - .08 * math.exp(-1.5), rel=1.e-13)


def _detector_probability():
    from h2physics.detector_reliability import evaluate_kofn_detector_reliability

    probabilities = (.1, .2, .3)
    result = evaluate_kofn_detector_reliability(("a", "b", "c"), probabilities, votes_required=2,
        common_cause_failure_probability=.02, mission_duration_s=3600., system_id="group", mission_id="mission",
        voting_logic_id="two-of-three", independent_probability_evidence_ids=("a", "b", "c"),
        common_cause_evidence_id="common")
    # Independent explicit enumeration of8 demand outcomes, unlike production DP.
    failure = sum(math.prod((1. - p) if alarm else p for p, alarm in zip(probabilities, outcome, strict=True))
                  for outcome in product((False, True), repeat=3) if sum(outcome) < 2)
    assert result.conditional_independent_vote_failure_probability == pytest.approx(failure)
    assert result.total_vote_failure_probability == pytest.approx(.02 + .98 * failure)


def _isolation_timing():
    from h2physics.adapters.alarm_valve_isolation import _compose
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand

    result = _compose(2., .3, 5., (ValveCommand(0., 5., .8, "open"),), "trip")
    assert [(c.start_s, c.end_s, c.target_stroke_fraction) for c in result] == [(0., 2.3, .8), (2.3, 5., 0.)]


def _impact_trial_algebra():
    from h2physics.adapters.droplet_impact import (
        FiniteSurfaceImpact,
        ImpactContext,
        ImpactOutcome,
        ImpactQualification,
        QualifiedImpactClosure,
        SurfacePatch,
    )
    from h2physics.adapters.droplet_transport import ParcelState
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    liquid, vapor = properties.saturated(1.e5, 0.), properties.saturated(1.e5, 1.)
    declared_coefficients = {"interpretation": "authored passive collision parameters"}
    location = SourceLocation("patch", "clock", "xyz", (0., 0., 0.), (0., 0., 1.))
    patch = SurfacePatch(location, 0., 1., 100., 300., 20., 350., 1.,
        "capacity", "mount", "dry", "thermal", Origin.SYNTHETIC, declared_coefficients)
    outcome = ImpactOutcome(1., .5, 1., (0., 0., 1.), 1., .2, 0.,
        "authored-coefficients", Origin.SYNTHETIC, declared_coefficients)
    domain = ImpactQualification("nominal", Origin.SYNTHETIC, (9.e4, 2.e5),
        (20., 350.), (.001, .1), (0., 10.), (0., 1000.), "lumped", "work", "phase")
    owner = FiniteSurfaceImpact(properties, patch,
        QualifiedImpactClosure(domain, lambda _context: outcome, declared_coefficients))
    diameter = (6. * .01 / (math.pi * liquid.density_kg_m3)) ** (1. / 3.)
    incident = ParcelState(1., (0., 0., 0.), (0., 0., -2.), .01, diameter, 1., 1., liquid, vapor)
    # Unit-level physical inputs only: no fabricated accepted ParcelTrace/run.
    context = ImpactContext(None, incident, patch, 300., liquid, vapor, 1.)
    result = owner._trial(context, outcome, .002)
    # Conservation gives recoil=-11/505, vapor velocity494/505; all remaining
    # liquid deposits. Lost incident kinetic energy heats the arrested patch.
    expected_heat = .02 - .001 * (494. / 505.)**2
    assert result.deposited_mass_kg == pytest.approx(.008)
    assert result.intermediate_recoil_velocity_m_s == pytest.approx((0., 0., -11. / 505.))
    assert result.total_heat_into_patch_j == pytest.approx(expected_heat, rel=2.e-14)
    expected_temperature = 300. + expected_heat / 100.
    expected_contact = 100. * (expected_temperature - liquid.temperature_k) * (1. - math.exp(-.002))
    assert result.available_contact_heat_j == pytest.approx(expected_contact, rel=2.e-13)


def _exposure_fluence():
    from h2physics.adapters.hyram_exposure import ExposureHistory, ExposureReceptor, HyRAMExposure

    target = Path(__file__).resolve().parents[1] / "artifacts/native_hyram_packages"
    if not (target / "hyram/__init__.py").is_file():
        raise RuntimeError("The declared actual HyRAM exposure dependency is unavailable")
    if str(target) not in sys.path:
        sys.path.append(str(target))
    engine = HyRAMExposure()
    history = ExposureHistory(ExposureReceptor("receptor", "xyz", (1., 0., 1.), "incident"),
        (0., 2.), (400., 1000.), "incident_radiant_flux", "W/m2", "linear", "clock",
        "source", "incident", Origin.SYNTHETIC)
    result = engine.thermal_dose(history, additivity_evidence_id="authored-linear-flux")
    # Only host fluence is compared. Native thermal-dose/probit physics is not
    # asserted and no native result is fabricated or replaced.
    assert result.fluence_j_m2 == pytest.approx(1400.)


def _obstacle_geometry():
    from h2physics.adapters.obstacle_dispersion import CartesianObstacle, CFDMesh

    obstacle = CartesianObstacle("solid", (1., 2., 2., 4., 1., 2.))
    mesh = CFDMesh((0., 4., 0., 8., 0., 4.), (8, 8, 8),
                   (obstacle,), "authored-box", "authored-grid", 1.e-9)
    # A 128m3 domain minus a 2m3 solid leaves 126m3; the solid occupies
    # 2*2*2 cells. No FDS field prediction is evaluated.
    assert mesh.spacing_m == pytest.approx((.5, 1., .5))
    assert obstacle.volume_m3 == pytest.approx(2.)
    assert mesh.fluid_volume_m3 == pytest.approx(126.)
    assert int(np.count_nonzero(mesh.solid_mask())) == 8



def _two_phase_nozzle():
    from scipy.integrate import quad

    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    upstream = properties.saturated(2.e5, .4)
    back = 1.9e5
    opening = NozzleOpening.circular("wet-reference", .002,
        effective_area_factor=.8, area_basis_id="authored-area")
    result = HomogeneousIsentropicNozzle(properties).solve(
        upstream, back_pressure_pa=back, opening=opening)
    downstream = properties.state_ps(back, upstream.entropy_j_kg_k)
    # Independently integrate mechanical work per mass along the actual wet
    # isentrope, instead of using the solver's stagnation-enthalpy subtraction.
    work, error = quad(lambda pressure: 1. / properties.state_ps(
        pressure, upstream.entropy_j_kg_k).density_kg_m3, back, 2.e5,
        epsabs=1.e-7, epsrel=1.e-10)
    assert upstream.phase == downstream.phase == "two_phase"
    assert error < 1.e-6
    expected = .8 * math.pi * .002**2 / 4. * downstream.density_kg_m3 * math.sqrt(2. * work)
    assert result.regime == "back_pressure_limited"
    assert result.mass_flow_kg_s == pytest.approx(expected, rel=2.e-8)


def _example_functions(name):
    import runpy
    return runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples" / name))


def _pool_fire_partition():
    example = _example_functions("pool_fire.py")
    model = example["build_model"](native_packages="artifacts/native_risk_packages")
    trace = example["run_example"](model)
    trace.require_current()
    step = trace.steps[0]
    # The retained real native consumption is an input to these host ledgers;
    # no assertion here independently qualifies PRCT burning/radiation physics.
    consumed = step.native_pool_result.burned_mass_kg
    released = step.native_pool_result.released_energy_j
    mh2 = next(species.molar_mass_kg_mol for species in model.reaction.species
               if species.identifier == model.hydrogen_id)
    assert step.oxygen_remaining_mol == pytest.approx(10. - .5 * consumed / mh2)
    assert step.water_product_mol == pytest.approx(consumed / mh2)
    assert step.radiation_export_j == pytest.approx(.18 * released)
    assert step.convective_export_j == pytest.approx(.55 * released)
    assert step.unallocated_release_j == pytest.approx(.27 * released)
    assert step.emitted_surface_power_w_m2 == pytest.approx(
        .18 * step.native_pool_result.heat_release_rate_w / math.pi)
    native_flux = step.receptors[0].native_sphere_result.heat_flux_w_m2
    assert step.receptors[0].incident_energy_j_m2 == pytest.approx(
        native_flux * step.native_pool_result.effective_duration_s)
    # A stable serialization must still reject a changed native result value.
    original = step.native_pool_result.burned_mass_kg
    object.__setattr__(step.native_pool_result, "burned_mass_kg", original + .001)
    try:
        with pytest.raises(ValueError, match="changed"):
            trace.require_current()
    finally:
        object.__setattr__(step.native_pool_result, "burned_mass_kg", original)
    trace.require_current()


def _flash_material_travel():
    import hashlib

    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, FlameSettings, MechanismBasis, ReactiveState
    from h2physics.adapters.flash_front import (
        FrontAdmission,
        FrontCell,
        MaterialContact,
        premixed_reference,
        run_material_front,
    )

    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    basis = MechanismBasis("installed-Cantera-h2o2:ohmech", hashlib.sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause;upstream-GRI-Mech-provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",), 300., 3500., 1.e4, 2.e6)
    owner = CanteraGas.from_yaml(raw, basis, phase_name="ohmech")
    initial = ReactiveState(310., 101325., {"H2": 2./6.76, "O2": 1./6.76, "N2": 3.76/6.76})
    # Explicit alternate native transport configuration gives a genuinely
    # monotone temperature profile; the production admission is unchanged.
    flame = owner.free_flame(initial, FlameSettings(.04,
        transport_model="mixture-averaged", soret_enabled=False))
    admission = FrontAdmission("authored-reference", "material", "clock", "mixture",
        "numerical-not-field-validation", .1, .9, 500., .005, .02, 1.e-8)
    reference = premixed_reference("actual-mixture-averaged", owner, flame, admission)
    speed = reference.flame_result.native_solution.velocity[0]
    travel = .2 / speed
    arrival = 10. + travel
    residence = reference.thermal_band_residence_s
    contact = MaterialContact("marker", "c2", arrival + residence / 4.,
                             arrival + residence * .75, "authored-contact")
    cells = tuple(FrontCell(f"c{i}", (i, 0, 0), reference) for i in range(3))
    trace = run_material_front(cells, spacing_m=(.1, .1, .1),
        ignition_cell_ids=("c0",), ignition_s=10., horizon_s=arrival + residence * 2.,
        clock_projection_tolerance_s=1.e-10, contacts=(contact,))
    # Constant actual native speed: distance/speed; only material-coordinate
    # arrival and interval overlap are checked, not flame-speed predictions.
    assert trace.arrival_s["c2"] == pytest.approx(arrival, abs=1.e-12)
    assert trace.contacts[0].overlap_s == pytest.approx(residence / 2., abs=2.e-14)
    trace.require_current()
    burn = trace.burned_cells[0]
    original = burn.arrival_s
    object.__setattr__(burn, "arrival_s", original + .1)
    try:
        with pytest.raises(ValueError, match="changed"):
            trace.require_current()
    finally:
        object.__setattr__(burn, "arrival_s", original)
    trace.require_current()


def _jet_fire_power_accounting():
    source = _example_functions("jet_fire_conservation.py")["build_source"](
        native_packages="artifacts/native_hyram_packages")
    # Actual native flame retained even when its physical gates reject it.
    # Only host source-power and residual arithmetic is compared here.
    native = source.native
    expected_power = native.mass_flow_rate * native.chem.DHc
    assert source.chemical_power_w == pytest.approx(expected_power, rel=1.e-12)
    assert source.radiant_power_residual_w == pytest.approx(
        native.Srad - native.Xrad * expected_power, abs=1.e-8)


@dataclass(frozen=True)
class FormulaCase:
    family: str
    target: str
    oracle: str
    scope: str
    invoke: object


CASES = (
    FormulaCase("release.two_phase", "HomogeneousIsentropicNozzle.solve", "Wet-isentrope integral of specific volume dP supplies independent kinetic work", "model_equation", _two_phase_nozzle),
    FormulaCase("combustion.pool_fire", "FinitePoolFire.run host ledgers", "Retained native fuel/heat to oxygen, water and .18/.55/.27 energy partition", "supporting_geometry_or_accounting", _pool_fire_partition),
    FormulaCase("combustion.flash_fire", "run_material_front host material travel/contact", "Actual native constant speed over .2m and half-residence overlap", "supporting_geometry_or_accounting", _flash_material_travel),
    FormulaCase("combustion.jet_fire", "run_hyram_flame host power accounting", "Actual native fuel mass rate times native heat and radiation residual", "supporting_geometry_or_accounting", _jet_fire_power_accounting),
    FormulaCase("dispersion.obstacle", "CFDMesh.fluid_volume_m3/solid_mask/spacing_m", "128m3 box minus2m3 obstacle and8 occupied cells", "supporting_geometry_or_accounting", _obstacle_geometry),
    FormulaCase("release.gas", "HomogeneousIsentropicNozzle.solve", "Closed-form constant-cp isentropic choked mass flux", "model_equation", _gas_nozzle),
    FormulaCase("release.liquid", "HomogeneousIsentropicNozzle.solve", "Bernoulli constant-density liquid mass flux", "model_equation", _liquid_nozzle),
    FormulaCase("release.near_field", "JetPlane.project", "Cartesian projection gives3m,4m,atan(4/3)", "supporting_geometry_or_accounting", _jet_coordinates),
    FormulaCase("release.droplets", "SaturatedParcelFlight.run", "Constant heat evaporates Q*dt/L mass", "model_equation", _parcel_evaporation),
    FormulaCase("surface.pool", "DeclaredGroundInflow.cumulative_mass_kg", "Piecewise constant inflow .01*2+.02*3=.08kg", "supporting_geometry_or_accounting", _pool_inflow_integral),
    FormulaCase("dispersion.buoyant_layer", "_plume_coefficient", "Independent cubed similarity coefficient1.92alpha²/pi²", "model_equation", _plume_coefficient),
    FormulaCase("dispersion.compartment_network", "simulate_hydrogen_compartment_network", "Single-room positive-flow exponential mixing", "model_equation", _compartment_mixing),
    FormulaCase("combustion.piston_engine", "SliderCrank.volume_m3/volume_rate_m3_s", "Right-angle slider-crank geometric solution", "supporting_geometry_or_accounting", _piston_geometry),
    FormulaCase("combustion.piston_engine", "integrate_engine_boundary_streams", "Integral of(1+t)(10+2t) gives148/3J", "supporting_geometry_or_accounting", _engine_stream_integral),
    FormulaCase("combustion.gas_turbine", "integrate_shaft_transient", "Nonzero constant-power kinetic-energy trajectory", "model_equation", _shaft_energy),
    FormulaCase("combustion.overpressure", "DetonableHydrogenEnergy.energy_j", "Participating mass times supplied heat=30MJ", "supporting_geometry_or_accounting", _participating_energy),
    FormulaCase("effects.fragment_trajectory", "integrate_fragment_flight", "Exact tanh fall with positive gravity and quadratic drag", "model_equation", _quadratic_drag_fragment),
    FormulaCase("effects.cryogenic", "_integrate_positive_threshold_deficit", "Trapezoidal O2 deficit .04fraction*s", "supporting_geometry_or_accounting", _oxygen_deficit),
    FormulaCase("facility.network", "FacilityContinuityAudit.audit", "Nonzero mass and enthalpy residual arithmetic", "supporting_geometry_or_accounting", _facility_continuity),
    FormulaCase("facility.monitoring", "evaluate_first_order_concentration_sensor", "Nonzero first-order step exponential", "model_equation", _sensor_step),
    FormulaCase("facility.detector_reliability", "evaluate_kofn_detector_reliability", "Enumerate all8 independent detector outcomes", "model_equation", _detector_probability),
    FormulaCase("facility.isolation", "alarm_valve_isolation._compose", "Action time2+.3=2.3s with exact split", "supporting_geometry_or_accounting", _isolation_timing),
    FormulaCase("release.impact", "FiniteSurfaceImpact._trial", "Finite recoil momentum and kinetic-to-contact heat at declared coefficients", "model_equation", _impact_trial_algebra),
    FormulaCase("effects.exposure", "HyRAMExposure.thermal_dose host fluence", "Linear-flux trapezoid(400+1000)/2*2=1400J/m2", "supporting_geometry_or_accounting", _exposure_fluence),
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.family}::{c.invoke.__name__}")
def test_independent_formula_answer(case, record_property):
    record_property("family", case.family)
    record_property("formula_target", case.target)
    record_property("oracle_description", case.oracle)
    record_property("formula_scope", case.scope)
    case.invoke()
