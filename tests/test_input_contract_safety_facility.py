"""Focused malformed-input checks for 33 declared safety/facility families.

These checks cover particular public parameter/boundary contracts, not all
inputs or physical validity of the original optional calculation engines.
"""

from dataclasses import dataclass, replace
from importlib import import_module
from types import SimpleNamespace

import pytest

from h2physics.core import Origin, PropertyBasis

INPUT_FAMILY_IDS = (
    "combustion.detonation", "combustion.equilibrium", "combustion.flash_fire",
    "combustion.gas_turbine", "combustion.jet_fire", "combustion.kinetics",
    "combustion.laminar_flame", "combustion.overpressure", "combustion.piston_engine",
    "combustion.pool_fire", "dispersion.buoyant_layer", "dispersion.compartment_network",
    "dispersion.enclosure", "dispersion.obstacle", "dispersion.outdoor", "effects.cryogenic",
    "effects.exposure", "effects.fragment_trajectory", "effects.heat_input", "effects.rupture",
    "facility.detector_reliability", "facility.isolation", "facility.monitoring",
    "facility.network", "facility.risk", "release.blowdown", "release.droplets",
    "release.gas", "release.impact", "release.liquid", "release.near_field",
    "release.two_phase", "surface.pool",
)


@dataclass(frozen=True)
class _InputCase:
    family: str
    target: str
    baseline: dict
    field: str
    bad_value: object
    message: str


def _cases(family, target, baseline, *invalid):
    return [_InputCase(family, target, baseline, field, value, message)
            for field, value, message in invalid]


_CASES = [
    *_cases("combustion.detonation", "adapters.detonation.DetonationSettings", {},
            ("sound_density_relative_step", 0., "perturbations"),
            ("native_jump_relative_tolerance", float("nan"), "finite")),
    *_cases("combustion.equilibrium", "adapters.cantera.ReactiveState",
            dict(temperature_k=300., pressure_pa=1.e5, mole_fractions={"H2": .5, "O2": .5}),
            ("temperature_k", -1., "temperature.*positive"),
            ("mole_fractions", {"H2": .7, "O2": .2}, "sum to one")),
    *_cases("combustion.kinetics", "adapters.cantera.ReactiveState",
            dict(temperature_k=300., pressure_pa=1.e5, mole_fractions={"H2": .5, "O2": .5}),
            ("pressure_pa", 0., "pressure.*positive"),
            ("mole_fractions", {"H2": 1.1, "O2": -.1}, "negative")),
    *_cases("combustion.flash_fire", "adapters.flash_front.FrontAdmission",
            dict(evidence_id="front", material_frame_id="material", clock_id="clock",
                 mixture_evidence_id="mixture", native_flame_qualification_id="flame",
                 low_temperature_progress=.1, high_temperature_progress=.9,
                 minimum_temperature_rise_k=10., maximum_relative_mass_flux_span=.01,
                 maximum_hp_residual_j_kg=1., maximum_element_residual=1.e-6),
            ("low_temperature_progress", .95, "ordered thermal progress"),
            ("minimum_temperature_rise_k", -1., "positive")),
    *_cases("combustion.gas_turbine", "combustion.open_brayton.OpenBraytonInputs",
            dict(mechanism_id="mechanism", process_window_id="window", air_temperature_k=300.,
                 air_pressure_pa=1.e5, air_mole_fractions=(("O2", .21), ("N2", .79)),
                 compressor_pressure_ratio=5., compressor_isentropic_efficiency=.8,
                 combustor_pressure_recovery=.98, hydrogen_fuel_to_air_mass_ratio=.01,
                 hydrogen_inlet_temperature_k=300., turbine_exhaust_pressure_pa=1.e5,
                 turbine_isentropic_efficiency=.85, hydrogen_lhv_j_kg=120.e6,
                 air_state_evidence_id="air", hydrogen_feed_evidence_id="fuel",
                 machine_parameter_evidence_id="machine", lhv_evidence_id="lhv"),
            ("compressor_pressure_ratio", 1., "ratio.*exceed one"),
            ("turbine_isentropic_efficiency", 1.2, "efficien")),
    *_cases("combustion.jet_fire", "adapters.hyram_flame.SteadyFlameWindow",
            dict(clock_id="clock", start_s=0., end_s=1., source_evidence_id="source",
                 steady_evidence_id="steady", origin=Origin.SYNTHETIC),
            ("end_s", -1., "increasing finite"),
            ("source_evidence_id", "", "identities")),
    *_cases("combustion.laminar_flame", "adapters.cantera.FlameSettings", dict(width_m=.03),
            ("width_m", 0., "width.*positive"),
            ("transport_model", "unqualified-model", "reviewed.*transport")),
    *_cases("combustion.overpressure", "adapters.hyram_overpressure.DetonableHydrogenEnergy",
            dict(participating_hydrogen_mass_kg=1., heat_of_combustion_j_kg=120.e6,
                 mass_evidence_id="mass", heat_evidence_id="heat", combustion_basis_id="basis",
                 source_id="source", origin=Origin.SYNTHETIC),
            ("participating_hydrogen_mass_kg", -1., "mass cannot be negative"),
            ("heat_of_combustion_j_kg", 0., "heat of combustion.*positive")),
    *_cases("combustion.piston_engine", "combustion.closed_charge_engine.SliderCrank",
            dict(bore_m=.08, stroke_m=.08, connecting_rod_m=.15,
                 compression_ratio=10., speed_rpm=1500.),
            ("connecting_rod_m", .01, "crank radius"),
            ("compression_ratio", 1., "exceed one")),
    *_cases("combustion.pool_fire", "adapters.pool_fire.PoolFireStage",
            dict(identifier="stage", start_s=0., end_s=1., clock_id="clock",
                 burning_flux_kg_m2_s=.001, burning_flux_evidence_id="burn",
                 sphere_diameter_m=1., sphere_geometry_evidence_id="geometry",
                 radiative_fraction=.2, convective_export_fraction=.3,
                 energy_partition_evidence_id="partition", origin=Origin.SYNTHETIC),
            ("burning_flux_kg_m2_s", -.01, "Burning flux.*negative"),
            ("radiative_fraction", .9, "exceeds released energy")),
    *_cases("dispersion.buoyant_layer", "buoyant_layer.TwoVentHydrogenLayerConfig",
            dict(compartment_height_m=3., floor_area_m2=10., source_height_m=.2,
                 lower_vent_area_m2=.1, upper_vent_area_m2=.1,
                 lower_discharge_coefficient=.6, upper_discharge_coefficient=.6,
                 ambient_pressure_pa=101325., ambient_temperature_k=300.,
                 initial_upper_layer_volume_m3=1., initial_upper_h2_mole_fraction=.01),
            ("source_height_m", 3.1, "below the ceiling"),
            ("upper_discharge_coefficient", 1.1, "discharge coefficients")),
    *_cases("dispersion.compartment_network", "compartment_network.WellMixedCompartment",
            dict(identifier="room", volume_m3=10., absolute_pressure_pa=101325.,
                 temperature_k=300., initial_hydrogen_mole_fraction=.1,
                 state_owner_id="owner", state_evidence_id="state"),
            ("volume_m3", 0., "volume.*positive"),
            ("initial_hydrogen_mole_fraction", 1.1, "fraction.*\\[0, 1\\]")),
    *_cases("dispersion.enclosure", "adapters.cantera_volume.GasHeatBoundary",
            dict(boundary_id="wall", clock_id="clock", support_start_s=0., support_end_s=1.,
                 environment_state=None, area_m2=1.),
            ("area_m2", -1., "wall area.*positive"),
            ("emissivity", 1.1, "emissivity.*\\[0, 1\\]")),
    *_cases("dispersion.obstacle", "adapters.obstacle_dispersion.CFDMesh",
            dict(bounds_m=(0., 1., 0., 1., 0., 1.), cells=(4, 4, 4), obstacles=(),
                 geometry_evidence_id="geometry", grid_evidence_id="grid",
                 geometry_tolerance_m=1.e-9),
            ("cells", (4, 3, 4), "at least four cells"),
            ("bounds_m", (0., 1., 0., 0., 0., 1.), "positive ordered extents")),
    *_cases("dispersion.outdoor", "release.SourceLocation",
            dict(source_id="jet", clock_id="clock", coordinate_frame_id="frame",
                 position_m=(0., 0., 1.), direction_unit=(1., 0., 0.)),
            ("position_m", (0., 1.), "three coordinates"),
            ("direction_unit", (2., 0., 0.), "unit vector")),
    *_cases("effects.cryogenic", "adapters.oxygen_deficiency.OxygenCriterion",
            dict(criterion_id="criterion", quantity="wet_oxygen_mole_fraction", threshold=.195,
                 comparator="below", minimum_pressure_pa=8.e4, maximum_pressure_pa=1.2e5,
                 minimum_elevation_m=0., maximum_elevation_m=1000.,
                 authority_reference="caller-reference", applicability_evidence_id="application"),
            ("threshold", 19.5, "fraction, not percent"),
            ("maximum_pressure_pa", 7.e4, "bounds must increase")),
    *_cases("effects.exposure", "adapters.hyram_exposure.ExposureHistory",
            dict(receptor=None, time_s=(0., 1.), values=(100., 200.),
                 quantity="incident_radiant_flux", unit="W/m2", interpolation="linear",
                 clock_id="clock", source_id="source", basis_id="incident", origin=Origin.SYNTHETIC),
            ("unit", "kW/m2", "Use explicit.*W/m2"),
            ("time_s", (0., 0.), "strictly increasing")),
    *_cases("effects.fragment_trajectory", "fragment_trajectory.FragmentLaunch",
            dict(fragment_id="fragment", mass_kg=1., reference_area_m2=.01, drag_coefficient=.5,
                 position_m=(0., 0., 1.), velocity_m_s=(1., 0., 1.), ground_z_m=0.,
                 frame_id="frame", evidence_id="launch"),
            ("mass_kg", -1., "mass_kg.*positive"),
            ("position_m", (0., 0., -1.), "above.*ground")),
    *_cases("effects.heat_input", "adapters.pifira_heat.ClosedHeatDomain",
            dict(minimum_pressure_pa=1.e5, maximum_pressure_pa=2.e6),
            ("maximum_pressure_pa", 1.e4, "Pressure domain must increase"),
            ("maximum_quality", 1.1, "two-phase quality domain")),
    *_cases("effects.rupture", "adapters.vessel_failure.HelprAxialFlaw",
            dict(outer_diameter_m=.22, wall_thickness_m=.01, flaw_depth_m=.002,
                 flaw_length_m=.01, location_factor=1., geometry_id="geometry",
                 defect_id="defect", evidence_id="flaw"),
            ("wall_thickness_m", .12, "positive inner radius"),
            ("flaw_depth_m", .009, "Anderson bounds")),
    *_cases("facility.isolation", "adapters.facility_protection.ProtectionAction",
            dict(identifier="isolate", mechanism_id="mechanism", target_id="feed",
                 action_kind="isolation", prior_mode_id="open", resulting_mode_id="closed",
                 latency_s=.1, evidence_id="command", interpretation="prescribed-counterfactual-replay",
                 origin=Origin.SYNTHETIC),
            ("latency_s", -.1, "cannot act before"),
            ("resulting_mode_id", "open", "actual change of mode")),
    *_cases("facility.monitoring", "adapters.gas_detection.FirstOrderConcentrationSensorConfig",
            dict(sensor_id="sensor", location_id="ceiling", clock_id="clock",
                 concentration_basis="H2-mole-fraction", concentration_unit="1",
                 response_time_constant_s=.5, maximum_input_sample_gap_s=1.,
                 sensor_evidence_id="sensor-data", response_parameter_evidence_id="tau",
                 model_evidence_id="lag-model"),
            ("response_time_constant_s", 0., "time constant.*positive"),
            ("concentration_unit", "", "concentration_unit")),
    *_cases("facility.network", "facility_continuity.FacilityStorageRate",
            dict(node_id="tank", basis=PropertyBasis("Hydrogen", "same-reference"),
                 mass_accumulation_kg_s=0., energy_accumulation_w=0.),
            ("mass_accumulation_kg_s", float("nan"), "mass_accumulation.*finite"),
            ("energy_accumulation_w", float("inf"), "energy_accumulation.*finite")),
    *_cases("facility.risk", "adapters.conditional_risk.ConditionalHarmBinding",
            dict(probability=.1, receptor_id="person", frame_id="frame", clock_id="clock",
                 support_s=(0., 1.), source_id="source", response_model_id="response",
                 position_m=(1., 0., 0.), evidence_ids=("caller-harm",), origin=Origin.SYNTHETIC),
            ("probability", 1.1, "probability.*\\[0,1\\]"),
            ("support_s", (1., 0.), "ordered exposure support")),
    *_cases("release.droplets", "adapters.droplet_transport.ParcelBoundary",
            dict(clock_id="clock", frame_id="frame", evidence_id="ambient",
                 carrier_density_kg_m3=1.2, carrier_viscosity_pa_s=1.8e-5,
                 carrier_velocity_m_s=(0., 0., 0.), gravity_m_s2=(0., 0., -9.81),
                 maximum_reynolds=1.e5, maximum_weber=10., surface_tension_n_m=.002,
                 maximum_laplace_pressure_fraction=.01),
            ("carrier_viscosity_pa_s", -1., "viscosity.*positive"),
            ("carrier_velocity_m_s", (0., 0.), "three|3")),
    *_cases("release.impact", "adapters.droplet_impact.ImpactQualification",
            dict(evidence_id="impact", origin=Origin.SYNTHETIC,
                 pressure_bounds_pa=(1.e5, 2.e5), wall_temperature_bounds_k=(20., 300.),
                 diameter_bounds_m=(1.e-4, .01), normal_speed_bounds_m_s=(0., 10.),
                 impact_weber_bounds=(0., 100.), lumped_capacity_evidence_id="lumped",
                 negligible_external_work_evidence_id="work", phase_equilibrium_evidence_id="phase"),
            ("diameter_bounds_m", (.01, 1.e-4), "bounds.*increasing"),
            ("normal_speed_bounds_m_s", (-1., 10.), "bounds.*nonnegative")),
    *_cases("release.near_field", "adapters.degali.JetPlane",
            dict(coordinate_frame_id="frame", origin_m=(0., 0., 0.),
                 horizontal_unit=(1., 0., 0.), vertical_unit=(0., 0., 1.)),
            ("horizontal_unit", (2., 0., 0.), "unit vector"),
            ("vertical_unit", (1., 0., 0.), "orthogonal")),
]


@pytest.mark.parametrize("case", _CASES,
                         ids=lambda c: f"{c.family}:{c.field}")
def test_parameter_input_rejection(case, record_property):
    module, symbol = case.target.rsplit(".", 1)
    factory = getattr(import_module("h2physics." + module), symbol)
    baseline = dict(case.baseline)
    # The enclosure wall receives a genuine typed gas environment, not a mock.
    if case.target.endswith("GasHeatBoundary"):
        from h2physics.adapters.cantera import ReactiveState
        baseline["environment_state"] = ReactiveState(300., 1.e5, {"N2": 1.})
    if case.target.endswith("ExposureHistory"):
        from h2physics.adapters.hyram_exposure import ExposureReceptor
        baseline["receptor"] = ExposureReceptor("person", "frame", (1., 0., 0.), "incident")
    accepted = factory(**baseline)
    record_property("family", case.family)
    record_property("input_target", "h2physics." + case.target)
    record_property("invalid_scenario", case.field)
    with pytest.raises(ValueError, match=case.message):
        replace(accepted, **{case.field: case.bad_value})


@pytest.mark.parametrize("family,phase", [
    ("release.gas", "gas"), ("release.liquid", "liquid"),
    ("release.two_phase", "two_phase"),
])
@pytest.mark.parametrize("scenario", ["negative_back_pressure", "excess_opening_fraction"])
def test_nozzle_phase_input_rejection(family, phase, scenario, record_property):
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    if phase == "gas":
        state = properties.state_pt(5.e6, 300.)
        assert state.phase == "gas" or state.phase.startswith("supercritical")
    elif phase == "liquid":
        state = properties.state_pt(5.e5, 20.)
        assert state.phase == "liquid"
    else:
        state = properties.saturated(5.e5, .5)
        assert state.phase == "two_phase"
    opening = NozzleOpening.circular("input-hole", .001,
                                     effective_area_factor=.8, area_basis_id="declared-area")
    nozzle = HomogeneousIsentropicNozzle(properties)
    record_property("family", family)
    record_property("input_target", "h2physics.release.HomogeneousIsentropicNozzle.solve")
    record_property("invalid_scenario", scenario)
    kwargs = dict(back_pressure_pa=1.e5, opening=opening)
    if scenario == "negative_back_pressure":
        kwargs["back_pressure_pa"] = -1.
        message = "back_pressure_pa.*positive"
    else:
        kwargs["opening_fraction"] = 1.1
        message = "Opening fraction"
    with pytest.raises(ValueError, match=message):
        nozzle.solve(state, **kwargs)


@pytest.mark.parametrize("scenario", ["nonfinite_clock", "negative_back_pressure"])
def test_bulk_blowdown_input_rejection(scenario, record_property):
    from h2physics.adapters.lh2dt import Lh2dtBulkNozzleOutflow, to_lh2dt_state
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    properties = CoolPropProperties("Hydrogen")
    state = properties.state_pt(5.e6, 300.)
    # Structural native-state aliases are populated solely from a real CP state.
    native_state = to_lh2dt_state(state, expected_basis=properties.basis, factory=SimpleNamespace)
    opening = NozzleOpening.circular("hole", .001, effective_area_factor=.8,
                                     area_basis_id="area")
    outflow = Lh2dtBulkNozzleOutflow(
        HomogeneousIsentropicNozzle(properties), opening,
        back_pressure_pa=-1. if scenario == "negative_back_pressure" else 1.e5,
        opening_fraction=1., flow_factory=dict,
    )
    record_property("family", "release.blowdown")
    record_property("input_target", "h2physics.adapters.lh2dt.Lh2dtBulkNozzleOutflow.sample")
    record_property("invalid_scenario", scenario)
    time = float("nan") if scenario == "nonfinite_clock" else 0.
    message = "time_s.*finite" if scenario == "nonfinite_clock" else "back_pressure_pa.*positive"
    with pytest.raises(ValueError, match=message):
        outflow.sample(time, native_state)


@pytest.mark.parametrize("scenario", ["outside_probability", "duplicate_detector"])
def test_detector_reliability_input_rejection(scenario, record_property):
    from h2physics.detector_reliability import evaluate_kofn_detector_reliability

    detector_ids = ("roof", "wall")
    probabilities = (.1, .2)
    if scenario == "outside_probability":
        probabilities = (.1, 1.1)
        message = "probability.*\\[0, 1\\]"
    else:
        detector_ids = ("roof", "roof")
        message = "uniquely identified"
    record_property("family", "facility.detector_reliability")
    record_property("input_target", "h2physics.detector_reliability.evaluate_kofn_detector_reliability")
    record_property("invalid_scenario", scenario)
    with pytest.raises(ValueError, match=message):
        evaluate_kofn_detector_reliability(
            detector_ids, probabilities, votes_required=1,
            common_cause_failure_probability=.01, mission_duration_s=3600.,
            system_id="group", mission_id="mission", voting_logic_id="one-of-two",
            independent_probability_evidence_ids=("roof-rate", "wall-rate"),
            common_cause_evidence_id="common-cause",
        )


@pytest.mark.parametrize("scenario", ["unsupported_spin", "missing_engine_identity"])
def test_pool_input_rejection(scenario, record_property):
    from h2physics.adapters.pool import NativeDynamicPool
    from h2physics.thermo import CoolPropProperties

    def must_not_run_native_pool(*args, **kwargs):
        raise AssertionError("Invalid pool inputs reached the native runner")

    normal = CoolPropProperties("Hydrogen")
    accepted = NativeDynamicPool(must_not_run_native_pool, normal, engine_id="declared-native-pool")
    assert accepted.properties is normal
    record_property("family", "surface.pool")
    record_property("input_target", "h2physics.adapters.pool.NativeDynamicPool.__init__")
    record_property("invalid_scenario", scenario)
    properties = CoolPropProperties("ParaHydrogen") if scenario == "unsupported_spin" else normal
    identity = "declared-native-pool" if scenario == "unsupported_spin" else ""
    message = "normal Hydrogen only" if scenario == "unsupported_spin" else "engine identity"
    with pytest.raises(ValueError, match=message):
        NativeDynamicPool(must_not_run_native_pool, properties, engine_id=identity)
