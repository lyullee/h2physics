"""Host-owned safety boundary/extreme checks; native physics is excluded."""

import importlib
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest
import test_formula_contract_safety_facility as nominal

from h2physics.core import Origin, PropertyBasis, ThermoState


def nozzle_limit(kind, area):
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    if kind == "gas":
        p = nominal._ConstantCpGasReference()
        s = p.state_pt(5e6, 300.0)
    elif kind == "liquid":
        p = nominal._IncompressibleReference()
        s = p.state_ps(8e5, 0.0)
    else:
        p = CoolPropProperties("Hydrogen")
        s = p.saturated(2e5, 0.4)
    opening = NozzleOpening("limit", area, 1.0, "authored-area")
    result = HomogeneousIsentropicNozzle(p).solve(
        s, back_pressure_pa=s.pressure_pa, opening=opening
    )
    assert result.mass_flow_kg_s == 0.0
    assert result.velocity_m_s == 0.0
    if kind == "gas":
        result = HomogeneousIsentropicNozzle(p).solve(s, back_pressure_pa=1e6, opening=opening)
        flux = 5e6 * math.sqrt(1.4 / (4000.0 * 300.0)) * (2 / 2.4) ** 3
        assert result.mass_flow_kg_s == pytest.approx(area * flux, rel=2e-8, abs=0.0)


def coordinates():
    from h2physics.adapters.degali import JetPlane
    from h2physics.release import SourceLocation

    plane = JetPlane("xyz", (1e12, 1e12, 1e12), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    source = SourceLocation(
        "source", "clock", "xyz", (1e12 + 1.0, 1e12, 1e12 + 2.0), (1.0, 0.0, 0.0)
    )
    assert plane.project(source) == pytest.approx((1.0, 2.0, 0.0), abs=0.0)


def droplet_zero():
    from h2physics.adapters.droplet_transport import (
        BoilingHeat,
        ParcelBoundary,
        SaturatedParcelFlight,
    )
    from h2physics.thermo import CoolPropProperties

    boundary = ParcelBoundary(
        "clock",
        "xyz",
        "carrier",
        1.2,
        1.8e-5,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, -9.81),
        1e5,
        100.0,
        0.002,
        0.01,
    )
    flight = SaturatedParcelFlight(
        CoolPropProperties("Hydrogen"),
        1e5,
        boundary,
        lambda s: BoilingHeat(0.0, "zero-heat"),
        force_approximation_evidence_id="heavy-sphere",
    )
    trace = flight.run(
        start_s=0.0,
        end_s=0.1,
        position_m=(0.0, 0.0, 10.0),
        velocity_m_s=(0.0, 0.0, 0.0),
        mass_kg=1e-4,
        residual_mass_floor_kg=1e-5,
        maximum_step_s=0.02,
        relative_tolerance=1e-9,
        absolute_tolerances=(1e-12,) * 17,
    )
    assert trace.evaporated_mass_kg == 0.0
    assert trace.states[-1].mass_kg == pytest.approx(1e-4, rel=1e-14, abs=0.0)


def inflow_scale():
    from h2physics.adapters.pool import DeclaredGroundInflow
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    target = Path(__file__).resolve().parents[1] / "artifacts/native_pool_packages"
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    cls = importlib.import_module("dynamiclh2poolx.inflow").DeclaredInflow
    inflow = DeclaredGroundInflow(
        cls((0.0, 1e6), (1e-18, 0.0)),
        SourceLocation("pool", "clock", "xyz", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        CoolPropProperties("Hydrogen").saturated(1e5, 0.0),
        0.0,
        2e6,
        Origin.SYNTHETIC,
        "tiny-feed-long-window",
        "window_end",
    )
    assert inflow.cumulative_mass_kg(0.0, clock_id="clock") == 0.0
    assert inflow.cumulative_mass_kg(2e6, clock_id="clock") == pytest.approx(
        1e-12, rel=1e-14, abs=0.0
    )


def plume_scale(alpha):
    from h2physics.buoyant_layer import _plume_coefficient

    c = _plume_coefficient(alpha)
    assert math.isfinite(c) and c > 0
    assert c**3 == pytest.approx(1.92 * alpha * alpha / math.pi**2, rel=1e-13, abs=0.0)


def compartment_limit():
    from h2physics.compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkModel,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )

    room = WellMixedCompartment("room", 1.0, 101325.0, 300.0, 0.0, "state", "state-data")
    feed = CompartmentMolarTransfer("feed", None, "room", (1.0,), "feed", "data", "clock", 1.0)
    exhaust = CompartmentMolarTransfer("out", "room", None, (1.0,), "out", "data", "clock")
    trace = simulate_hydrogen_compartment_network(
        CompartmentNetworkModel((room,), (feed, exhaust), "clock"), time_samples_s=(0.0, 4000.0)
    )
    assert trace.hydrogen_mole_fraction[-1, 0] == pytest.approx(1.0, abs=1e-9)
    assert np.all(
        (trace.hydrogen_mole_fraction >= 0.0) & (trace.hydrogen_mole_fraction <= 1.0 + 1e-9)
    )


def piston_extrema():
    from h2physics.combustion.closed_charge_engine import SliderCrank

    g = SliderCrank(0.08, 0.08, 0.15, 1e6, 1500.0)
    swept = math.pi * 0.08**2 / 4 * 0.08
    assert g.volume_m3(0.0) == pytest.approx(swept / (1e6 - 1), rel=1e-13, abs=0.0)
    assert g.volume_m3(math.pi) == pytest.approx(swept + swept / (1e6 - 1), rel=1e-13, abs=0.0)
    assert g.volume_rate_m3_s(0.0) == 0.0


def shaft_scale():
    from h2physics.combustion.shaft_transient import ShaftTransientInputs, integrate_shaft_transient

    x = ShaftTransientInputs(
        (0.0, 100.0),
        (1e12, 1e12),
        (1e12, 1e12),
        (0.0, 0.0),
        (0.0, 100.0),
        1e6,
        1e6,
        1.0,
        2e6,
        0.0,
        0.0,
        1e-10,
        1e-6,
        10.0,
        "shaft",
        "powers",
        "load",
        "inertia",
    )
    trace = integrate_shaft_transient(x)
    assert trace.kinetic_energy_j[-1] == pytest.approx(5e17, rel=1e-14, abs=0.0)
    assert trace.speed_rad_s[-1] == pytest.approx(1e6, rel=1e-14, abs=0.0)


def energy_scale(mass):
    from h2physics.adapters.hyram_overpressure import DetonableHydrogenEnergy

    result = DetonableHydrogenEnergy(mass, 1e8, "mass", "heat", "LHV", "source", Origin.SYNTHETIC)
    assert math.isfinite(result.energy_j)
    assert result.energy_j == pytest.approx(mass * 1e8, rel=1e-15, abs=0.0)


def fragment_terminal():
    from h2physics.fragment_trajectory import (
        FragmentFlightEnvironment,
        FragmentFlightSettings,
        FragmentLaunch,
        integrate_fragment_flight,
    )

    k = 0.15
    terminal = math.sqrt(9.81 / k)
    launch = FragmentLaunch(
        "fragment", 2.0, 1.0, 0.5, (0.0, 0.0, 1e4), (0.0, 0.0, -terminal), 0.0, "xyz", "launch"
    )
    env = FragmentFlightEnvironment(
        lambda z: 1.2,
        lambda p, t: np.zeros(3),
        np.array((0.0, 0.0, -9.81)),
        "xyz",
        "env",
        "rho",
        "wind",
    )
    trace = integrate_fragment_flight(
        launch, env, FragmentFlightSettings("clock", np.array((0.0, 100.0)))
    )
    assert trace.velocity_m_s[-1, 2] == pytest.approx(-terminal, rel=1e-9, abs=0.0)
    assert trace.position_m[-1, 2] == pytest.approx(1e4 - terminal * 100.0, rel=1e-10, abs=0.0)


def oxygen_limits():
    from h2physics.adapters.oxygen_threshold_integral import _integrate_positive_threshold_deficit

    assert _integrate_positive_threshold_deficit((0.0, 1e12), (0.25, 0.25), 0.2) == (0.0,)
    assert _integrate_positive_threshold_deficit((0.0, 1e12), (0.2 - 1e-12, 0.2 - 1e-12), 0.2)[
        0
    ] == pytest.approx((0.2 - (0.2 - 1e-12)) * 1e12, rel=1e-14, abs=0.0)


def facility_scale():
    from h2physics.facility_continuity import (
        ExternalFacilityRate,
        FacilityContinuityAudit,
        FacilityContinuityFrame,
        FacilityNode,
        FacilityStorageRate,
    )

    basis = PropertyBasis("authored", "energy-reference")
    state = ThermoState(basis, 1e5, 300.0, 1.0, 1e100, 1e100, 0.0, "gas")
    frame = FacilityContinuityFrame(
        "clock",
        1.0,
        (),
        (ExternalFacilityRate("in", "node", "port", 1e100, state, 0.0, 0.0),),
        (FacilityStorageRate("node", basis, 1e100, 1e200),),
    )
    result = FacilityContinuityAudit((FacilityNode("node", basis),)).audit(
        frame, require_closed=False
    )
    assert result.mass_residual_kg_s == 0.0
    assert result.node_energy_residual_w == 0.0


def sensor_limit(tau):
    from h2physics.adapters.gas_detection import (
        FirstOrderConcentrationSensorConfig,
        evaluate_first_order_concentration_sensor,
    )

    c = FirstOrderConcentrationSensorConfig(
        "s", "roof", "clock", "H2-mole-fraction", "1", tau, 2.0, "sensor", "tau", "first-order"
    )
    trace = evaluate_first_order_concentration_sensor(
        c,
        time_s=(0.0, 1.0),
        true_concentration=(1.0, 1.0),
        initial_indication=0.0,
        source_evidence_id="step",
        operating_mode_id="boundary",
        episode_id="episode",
        origin=Origin.SYNTHETIC,
    )
    expected = -math.expm1(-1.0 / tau)
    assert trace.indicated_concentration[-1] == pytest.approx(expected, rel=1e-13, abs=0.0)
    assert 0.0 <= trace.indicated_concentration[-1] <= 1.0


def detector_limit(prob):
    from h2physics.detector_reliability import evaluate_kofn_detector_reliability

    r = evaluate_kofn_detector_reliability(
        ("a", "b"),
        (prob, prob),
        votes_required=1,
        common_cause_failure_probability=0.0,
        mission_duration_s=1e12,
        system_id="sys",
        mission_id="mission",
        voting_logic_id="one-of-two",
        independent_probability_evidence_ids=("a", "b"),
        common_cause_evidence_id="zero-common",
    )
    assert r.total_vote_failure_probability == pytest.approx(prob**2, rel=1e-14, abs=0.0)
    assert 0 <= r.total_vote_failure_probability <= 1


def isolation_limits():
    from h2physics.adapters.alarm_valve_isolation import _compose
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand

    commands = (ValveCommand(0.0, 1e12, 0.9, "open"),)
    r = _compose(0.0, 0.0, 1e12, commands, "trip")
    assert (
        len(r) == 1
        and r[0].start_s == 0.0
        and r[0].end_s == 1e12
        and r[0].target_stroke_fraction == 0.0
    )
    with pytest.raises(ValueError, match="before"):
        _compose(1e12, 0.0, 1e12, commands, "trip")


def obstacle_scale(scale):
    from h2physics.adapters.obstacle_dispersion import CartesianObstacle, CFDMesh

    mesh = CFDMesh(
        (0.0, 4 * scale, 0.0, 8 * scale, 0.0, 4 * scale),
        (8, 8, 8),
        (CartesianObstacle("solid", (scale, 2 * scale, 2 * scale, 4 * scale, scale, 2 * scale)),),
        "box",
        "grid",
        scale * 1e-9,
    )
    assert mesh.fluid_volume_m3 == pytest.approx(126 * scale**3, rel=1e-13, abs=0.0)
    assert int(np.count_nonzero(mesh.solid_mask())) == 8


def pool_partition_limits():
    e = nominal._example_functions("pool_fire.py")
    model = e["build_model"](native_packages="artifacts/native_risk_packages")
    stage = replace(e["stages"](model)[0], radiative_fraction=0.0, convective_export_fraction=1.0)
    trace = e["run_example"](model, schedule=(stage,))
    step = trace.steps[0]
    assert step.radiation_export_j == 0.0 and step.unallocated_release_j == 0.0
    assert step.convective_export_j == step.chemical_energy_j
    assert step.receptors[0].incident_energy_j_m2 == 0.0
    trace.require_current()


def exposure_zero():
    from h2physics.adapters.hyram_exposure import ExposureHistory, ExposureReceptor, HyRAMExposure

    target = Path(__file__).resolve().parents[1] / "artifacts/native_hyram_packages"
    if str(target) not in sys.path:
        sys.path.append(str(target))
    history = ExposureHistory(
        ExposureReceptor("r", "xyz", (1.0, 0.0, 1.0), "incident"),
        (0.0, 1e12),
        (0.0, 0.0),
        "incident_radiant_flux",
        "W/m2",
        "linear",
        "clock",
        "source",
        "incident",
        Origin.SYNTHETIC,
    )
    result = HyRAMExposure().thermal_dose(history, additivity_evidence_id="zero-input")
    assert result.fluence_j_m2 == 0.0


def impact_contact_limit():
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
    liquid = properties.saturated(1e5, 0.0)
    vapor = properties.saturated(1e5, 1.0)
    declared = {"meaning": "authored passive coefficient limits"}
    patch = SurfacePatch(
        SourceLocation("patch", "clock", "xyz", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        0.0,
        1.0,
        100.0,
        300.0,
        20.0,
        350.0,
        1.0,
        "capacity",
        "mount",
        "dry",
        "thermal",
        Origin.SYNTHETIC,
        declared,
    )
    outcome = ImpactOutcome(
        1.0, 0.5, 1.0, (0.0, 0.0, 1.0), 1e12, 1.0, 0.0, "coefficients", Origin.SYNTHETIC, declared
    )
    domain = ImpactQualification(
        "limits",
        Origin.SYNTHETIC,
        (9e4, 2e5),
        (20.0, 350.0),
        (0.001, 0.1),
        (0.0, 10.0),
        (0.0, 1000.0),
        "lumped",
        "work",
        "phase",
    )
    owner = FiniteSurfaceImpact(
        properties, patch, QualifiedImpactClosure(domain, lambda c: outcome, declared)
    )
    diameter = (6 * 0.01 / (math.pi * liquid.density_kg_m3)) ** (1 / 3)
    incident = ParcelState(
        1.0, (0.0, 0.0, 0.0), (0.0, 0.0, -2.0), 0.01, diameter, 1.0, 1.0, liquid, vapor
    )
    context = ImpactContext(None, incident, patch, 300.0, liquid, vapor, 1.0)
    trial = owner._trial(context, outcome, 0.0)
    assert (
        trial.deposited_mass_kg == 0.01
        and trial.rebound_mass_kg == 0.0
        and trial.vapor_mass_kg == 0.0
    )
    assert trial.total_heat_into_patch_j == pytest.approx(0.02, rel=1e-14, abs=0.0)
    assert trial.available_contact_heat_j == pytest.approx(
        100 * (300.0002 - liquid.temperature_k), rel=1e-14, abs=0.0
    )


def jet_zero_distance():
    source = nominal._example_functions("jet_fire_conservation.py")["build_source"](
        native_packages="artifacts/native_hyram_packages"
    )
    # A genuine emitter location creates the zero-distance geometric singularity.
    # The host must reject it before any native radiation invocation.
    point = (float(source.native.x[0]), source.location.position_m[1], float(source.native.y[0]))
    with pytest.raises(ValueError, match="excluded native emitter neighborhood"):
        source.irradiance(
            (point,),
            relative_humidity=0.5,
            minimum_source_distance_m=1e-12,
            allow_rejected_flame=True,
        )


def flash_length_limits():
    import hashlib

    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, FlameSettings, MechanismBasis, ReactiveState
    from h2physics.adapters.flash_front import (
        FrontAdmission,
        FrontCell,
        premixed_reference,
        run_material_front,
    )

    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    basis = MechanismBasis(
        "installed-Cantera-h2o2:ohmech",
        hashlib.sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause;upstream-GRI-Mech-provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",),
        300.0,
        3500.0,
        1e4,
        2e6,
    )
    owner = CanteraGas.from_yaml(raw, basis, phase_name="ohmech")
    flame = owner.free_flame(
        ReactiveState(310.0, 101325.0, {"H2": 2 / 6.76, "O2": 1 / 6.76, "N2": 3.76 / 6.76}),
        FlameSettings(0.04, transport_model="mixture-averaged", soret_enabled=False),
    )
    reference = premixed_reference(
        "native-baseline",
        owner,
        flame,
        FrontAdmission(
            "reference",
            "material",
            "clock",
            "mixture",
            "numerical-only",
            0.1,
            0.9,
            500.0,
            0.005,
            0.02,
            1e-8,
        ),
    )
    speed = flame.native_solution.velocity[0]
    for length in (1e-6, 1e6):
        cells = (FrontCell("a", (0, 0, 0), reference), FrontCell("b", (1, 0, 0), reference))
        arrival = length / speed
        trace = run_material_front(
            cells,
            spacing_m=(length, length, length),
            ignition_cell_ids=("a",),
            ignition_s=0.0,
            horizon_s=arrival + reference.thermal_band_residence_s,
            clock_projection_tolerance_s=1e-12,
        )
        assert trace.arrival_s["b"] == pytest.approx(arrival, rel=1e-13, abs=0.0)
        trace.require_current()


@dataclass(frozen=True)
class Case:
    family: str
    scenario: str
    target: str
    scope: str
    invoke: object


CASES = []


def add(family, scenario, target, check, scope="model_equation"):
    CASES.append(Case(family, scenario, target, scope, check))


for kind in ("gas", "liquid", "two_phase"):
    for area in (1e-24, 1e6):
        add(
            "release." + kind,
            f"equal_pressure_and_area_{area:g}",
            "HomogeneousIsentropicNozzle.solve",
            lambda k=kind, a=area: nozzle_limit(k, a),
        )
add(
    "release.near_field",
    "large_origin_small_resolved_offset",
    "JetPlane.project",
    coordinates,
    "supporting_geometry_or_accounting",
)
add("release.droplets", "zero_boiling_heat", "SaturatedParcelFlight.run", droplet_zero)
add(
    "surface.pool",
    "tiny_flow_long_duration",
    "DeclaredGroundInflow.cumulative_mass_kg",
    inflow_scale,
    "supporting_geometry_or_accounting",
)
for a in (1e-12, 1e6):
    add(
        "dispersion.buoyant_layer",
        f"entrainment_scale_{a:g}",
        "_plume_coefficient",
        lambda a=a: plume_scale(a),
    )
add(
    "dispersion.compartment_network",
    "pure_feed_long_time_limit",
    "simulate_hydrogen_compartment_network",
    compartment_limit,
)
add(
    "combustion.piston_engine",
    "dead_centres_compression_1e6",
    "SliderCrank",
    piston_extrema,
    "supporting_geometry_or_accounting",
)
add(
    "combustion.gas_turbine",
    "large_energy_exact_power_balance",
    "integrate_shaft_transient",
    shaft_scale,
)
for m in (0.0, 1e-200, 1e200):
    add(
        "combustion.overpressure",
        f"mass_scale_{m:g}",
        "DetonableHydrogenEnergy.energy_j",
        lambda m=m: energy_scale(m),
        "supporting_geometry_or_accounting",
    )
add(
    "effects.fragment_trajectory",
    "terminal_velocity_invariant_100s",
    "integrate_fragment_flight",
    fragment_terminal,
)
add(
    "effects.cryogenic",
    "zero_and_tiny_deficit_long_clock",
    "_integrate_positive_threshold_deficit",
    oxygen_limits,
    "supporting_geometry_or_accounting",
)
add(
    "facility.network",
    "balanced_1e200_energy",
    "FacilityContinuityAudit.audit",
    facility_scale,
    "supporting_geometry_or_accounting",
)
for tau in (1e-12, 1e12):
    add(
        "facility.monitoring",
        f"response_time_{tau:g}",
        "evaluate_first_order_concentration_sensor",
        lambda tau=tau: sensor_limit(tau),
    )
for p in (0.0, 1.0, 1e-150):
    add(
        "facility.detector_reliability",
        f"failure_probability_{p:g}",
        "evaluate_kofn_detector_reliability",
        lambda p=p: detector_limit(p),
    )
add(
    "facility.isolation",
    "zero_latency_and_end_of_support",
    "alarm_valve_isolation._compose",
    isolation_limits,
    "supporting_geometry_or_accounting",
)
for scale in (1e-6, 1e6):
    add(
        "dispersion.obstacle",
        f"length_scale_{scale:g}",
        "CFDMesh.fluid_volume_m3/solid_mask",
        lambda s=scale: obstacle_scale(s),
        "supporting_geometry_or_accounting",
    )
add(
    "combustion.pool_fire",
    "zero_radiation_full_convection_partition",
    "FinitePoolFire.run",
    pool_partition_limits,
    "supporting_geometry_or_accounting",
)
add(
    "effects.exposure",
    "zero_flux_1e12_seconds",
    "HyRAMExposure host fluence",
    exposure_zero,
    "supporting_geometry_or_accounting",
)

add(
    "release.impact",
    "zero_vapor_long_contact_heat_limit",
    "FiniteSurfaceImpact._trial",
    impact_contact_limit,
)
add(
    "combustion.flash_fire",
    "material_cell_lengths_1e-6_to_1e6",
    "run_material_front",
    flash_length_limits,
    "supporting_geometry_or_accounting",
)
add(
    "combustion.jet_fire",
    "zero_native_emitter_distance_rejected",
    "HyRAMFlameRun.irradiance host geometry guard",
    jet_zero_distance,
    "supporting_geometry_or_accounting",
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.family + "::" + c.scenario)
def test_extreme_host_contract(case, record_property):
    record_property("family", case.family)
    record_property("extreme_scenario", case.scenario)
    record_property("extreme_target", case.target)
    record_property("scope_kind", case.scope)
    case.invoke()
