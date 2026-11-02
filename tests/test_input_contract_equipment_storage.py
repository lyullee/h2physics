"""Representative public input rejection for 28 equipment/storage families.

These are parameter preflight checks, not physical-model qualification. Each
case first constructs an admissible baseline, then changes one declared input.
The optional LH2DT cases inspect its installed parameter API only; they never
integrate equipment or compare the native engine's physical predictions.
"""

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from h2physics.adapters.carrier_conversion import CarrierProcessEvidence
from h2physics.adapters.counterflow_heat_exchanger import CounterflowBoundary
from h2physics.adapters.cryo_compressed import CryoCompressedDomain
from h2physics.adapters.finite_adsorption_vessel import AdsorptionVesselGeometry
from h2physics.adapters.lh2dt_compressor import CompressorEnvelope
from h2physics.adapters.lh2dt_instrumentation import TransmitterEvidence
from h2physics.adapters.lh2dt_insulation import InsulationEvidence, WallHeatAllocation
from h2physics.adapters.lh2dt_pump_operation import PumpSpeedActuator, PumpSpeedCommand
from h2physics.adapters.lh2dt_relief import ReliefEventSettings
from h2physics.adapters.lh2dt_reliquefier import ReliquefactionDomain
from h2physics.adapters.lh2dt_spin import SpinDomain
from h2physics.adapters.lh2dt_valve_actuator import StrokeActuator, ValveCommand
from h2physics.adapters.lh2dt_vent import VentEnvelope
from h2physics.adapters.psa import BedFaceTransfers
from h2physics.adapters.underground_storage import UndergroundDomain
from h2physics.core import Origin, PropertyBasis, ThermoState
from h2physics.hydraulics import DarcyGeometry
from h2physics.mixtures import GasComposition
from h2physics.observations import Variable
from h2physics.storage.finite_hydride import (
    FiniteHydrideDomain,
    FiniteHydrideHeatBoundary,
    FiniteHydrideHeatInput,
)
from h2physics.storage.hydride import VanthoffPlateau
from h2physics.storage.hydride_compressor import HydrideCompressorStage
from h2physics.storage.microsphere import MicrosphereDomain
from h2physics.storage.porous_reservoir import PorousReservoirGeometry
from h2physics.storage.solid_reaction import SolidReactionStep
from h2physics.thermo.coolprop import CoolPropProperties

INPUT_FAMILY_IDS = (
    "thermo.pure_fluid", "thermo.spin", "thermo.mixtures",
    "equipment.gas_tank", "equipment.lh2_tank", "equipment.insulation",
    "equipment.gas_pipe", "equipment.two_phase_pipe", "equipment.valve",
    "equipment.relief", "equipment.pump", "equipment.compressor",
    "equipment.heat_exchanger", "equipment.vaporizer", "equipment.reliquefier",
    "equipment.vent", "equipment.instrument", "storage.cryo_compressed",
    "storage.adsorption", "storage.adsorption_thermal", "storage.hydride_equilibrium",
    "storage.hydride_dynamic", "storage.hydride_compressor", "storage.carrier_reaction",
    "storage.solid_reaction", "storage.microsphere", "storage.underground",
    "storage.porous_reservoir",
)


def _native_type(name):
    """Select the separately installed native snapshot without skips or copies."""
    target = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
    if not (target / "lh2dt/__init__.py").is_file():
        raise RuntimeError("The declared LH2DT input-contract dependency is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return getattr(importlib.import_module("lh2dt"), name)


def _native_constructor(name, **kwargs):
    return _native_type(name)(**kwargs)


@dataclass(frozen=True)
class InputCase:
    family: str
    scenario: str
    target: str
    factory: object
    baseline: dict
    changes: dict
    message: str


def _cases():
    cases = []

    def add(family, factory, baseline, mutations, *, target=None):
        label = target or f"{factory.__module__}.{factory.__qualname__}"
        for scenario, changes, message in mutations:
            cases.append(InputCase(family, scenario, label, factory, baseline, changes, message))

    add("thermo.pure_fluid", ThermoState,
        dict(basis=PropertyBasis("Hydrogen", "authored-input-only"), pressure_pa=1e5,
             temperature_k=300., density_kg_m3=1., enthalpy_j_kg=1e6,
             internal_energy_j_kg=9e5, entropy_j_kg_k=100., phase="gas"),
        [("negative-pressure", {"pressure_pa": -1.}, "pressure_pa"),
         ("nonfinite-temperature", {"temperature_k": float("nan")}, "temperature_k")])
    add("thermo.spin", SpinDomain,
        dict(minimum_temperature_k=15., maximum_temperature_k=500.,
             reference_rotational_level=9, cutoff_absolute_tolerance=1e-6,
             evidence_id="authored-spin-input-domain"),
        [("inverted-temperature-domain", {"minimum_temperature_k": 501.}, "bounds"),
         ("noninteger-rotational-cutoff", {"reference_rotational_level": 3.5}, "integer")])
    add("thermo.mixtures", GasComposition,
        dict(composition_id="authored-mixture", species=("H2", "N2"),
             mole_fractions=(.2, .8), molar_masses_kg_mol=(.00201588, .0280134)),
        [("unnormalized-fractions", {"mole_fractions": (.2, .7)}, "normalized"),
         ("mismatched-species-axis", {"molar_masses_kg_mol": (.00201588,)}, "one-dimensional")])

    def tank_state(**values):
        return _native_constructor("TankState", **values)

    add("equipment.gas_tank", tank_state,
        dict(hydrogen_mass_kg=1., hydrogen_internal_energy_J=1e6, wall_temperature_K=300.),
        [("negative-tank-inventory", {"hydrogen_mass_kg": -1.}, "hydrogen_mass_kg"),
         ("nonfinite-wall-temperature", {"wall_temperature_K": float("nan")}, "wall_temperature_K")],
        target="lh2dt.TankState")

    def tank_geometry(**values):
        return _native_constructor("TankGeometry", **values)

    add("equipment.lh2_tank", tank_geometry,
        dict(volume_m3=.1, wall_heat_capacity_J_K=1000., ambient_UA_W_K=.1,
             fluid_wall_UA_W_K=1.),
        [("zero-vessel-volume", {"volume_m3": 0.}, "volume_m3"),
         ("nonfinite-wall-capacity", {"wall_heat_capacity_J_K": float("inf")}, "wall_heat_capacity")],
        target="lh2dt.TankGeometry")
    add("equipment.insulation", InsulationEvidence,
        dict(geometry_id="geometry", closure_id="closure", residual_gas_id="gas",
             pressure_evidence_id="vacuum", source_ids=("authored",), origin=Origin.SYNTHETIC),
        [("gauge-vacuum-pressure-basis", {"pressure_basis": "gauge"}, "absolute"),
         ("missing-geometry-evidence", {"geometry_id": ""}, "Geometry")])
    add("equipment.insulation", WallHeatAllocation,
        dict(zone_ids=("wall-a", "wall-b"), area_fractions=(.5, .5),
             localized_path_fractions={}, evidence_id="authored-allocation"),
        [("unnormalized-area-fractions", {"area_fractions": (.4, .4)}, "sum to one")])
    add("equipment.gas_pipe", DarcyGeometry,
        dict(length_m=10., diameter_m=.02, roughness_m=1e-6, local_loss_coefficient=0.),
        [("negative-pipe-length", {"length_m": -1.}, "length_m"),
         ("nonfinite-bore", {"diameter_m": float("nan")}, "diameter_m")])

    def hem_pipe(**values):
        return _native_constructor("HEMPipe", **values)

    add("equipment.two_phase_pipe", hem_pipe,
        dict(length_m=10., inner_diameter_m=.02, roughness_m=1e-6),
        [("zero-hem-bore", {"inner_diameter_m": 0.}, "inner_diameter_m"),
         ("negative-hem-roughness", {"roughness_m": -1e-6}, "roughness")],
        target="lh2dt.HEMPipe")
    add("equipment.valve", ValveCommand,
        dict(start_s=0., end_s=1., target_stroke_fraction=.5, command_id="valve-command"),
        [("reversed-valve-clock", {"end_s": -1.}, "interval"),
         ("overfull-stroke", {"target_stroke_fraction": 1.1}, "target_stroke_fraction")])
    add("equipment.valve", StrokeActuator,
        dict(actuator_id="valve", opening_rate_fraction_s=1., closing_rate_fraction_s=1.,
             initial_stroke_fraction=0., clock_id="operation", evidence_id="authored"),
        [("negative-opening-rate", {"opening_rate_fraction_s": -1.}, "opening_rate")])
    add("equipment.relief", ReliefEventSettings, {},
        [("negative-pressure-tolerance", {"pressure_tolerance_pa": -1.}, "pressure_tolerance_pa"),
         ("noninteger-event-count", {"maximum_events": 2.5}, "positive integers")])
    add("equipment.pump", PumpSpeedCommand,
        dict(command_id="pump-command", start_s=0., end_s=1., target_speed_fraction=.5),
        [("reversed-pump-clock", {"end_s": -1.}, "interval"),
         ("invalid-stop-speed", {"mode": "stop"}, "zero speed")])
    add("equipment.pump", PumpSpeedActuator,
        dict(actuator_id="pump", clock_id="operation", initial_speed_fraction=0.,
             ramp_up_fraction_s=1., ramp_down_fraction_s=1., evidence_id="authored"),
        [("negative-speed-ramp", {"ramp_up_fraction_s": -1.}, "ramp_up_fraction_s")])
    add("equipment.compressor", CompressorEnvelope,
        dict(minimum_pressure_pa=1e5, maximum_pressure_pa=1e7, minimum_temperature_k=200.,
             maximum_temperature_k=600., minimum_mass_flow_kg_s=.01,
             maximum_mass_flow_kg_s=1., evidence_id="authored-compressor-envelope"),
        [("inverted-compressor-pressure", {"maximum_pressure_pa": 1e4}, "bounds"),
         ("nonfinite-compressor-flow", {"maximum_mass_flow_kg_s": float("nan")}, "maximum_mass_flow")])
    add("equipment.heat_exchanger", CounterflowBoundary,
        dict(hot_mass_flow_kg_s=1., cold_mass_flow_kg_s=1., hot_inlet_enthalpy_j_kg=1e6,
             cold_inlet_enthalpy_j_kg=1e5, hot_pressure_pa_absolute=(1e5, 1e5),
             cold_pressure_pa_absolute=(1e5, 1e5), source_id="authored-hx-boundary"),
        [("negative-hot-flow", {"hot_mass_flow_kg_s": -1.}, "hot_mass_flow"),
         ("nonfinite-cold-pressure", {"cold_pressure_pa_absolute": (1e5, float("nan"))}, "cold_pressure")])

    def vaporizer(**values):
        return _native_constructor("DynamicVaporizer", **values)

    add("equipment.vaporizer", vaporizer,
        dict(fluid_volume_m3=.01, wall_heat_capacity_J_K=1000., fluid_wall_UA_W_K=1.,
             ambient_temperature_K=300., ambient_UA_W_K=1., maximum_heat_W=1000.),
        [("negative-vaporizer-volume", {"fluid_volume_m3": -1.}, "fluid_volume_m3"),
         ("nonfinite-vaporizer-wall-capacity", {"wall_heat_capacity_J_K": float("nan")}, "wall_heat_capacity")],
        target="lh2dt.DynamicVaporizer")
    add("equipment.reliquefier", ReliquefactionDomain,
        dict(minimum_pressure_pa=1e4, maximum_pressure_pa=1e7,
             minimum_temperature_k=14., maximum_temperature_k=500., evidence_id="authored"),
        [("reversed-cold-pressure-domain", {"maximum_pressure_pa": 1e3}, "bounds"),
         ("negative-cold-temperature", {"minimum_temperature_k": -1.}, "minimum_temperature")])
    add("equipment.vent", VentEnvelope,
        dict(minimum_pressure_pa=1e4, maximum_pressure_pa=1e7, minimum_temperature_k=20.,
             maximum_temperature_k=500., maximum_pressure_fraction=.1,
             maximum_density_change_fraction=.1, maximum_mach_number=.2, evidence_id="authored"),
        [("supersonic-scope-for-low-mach-vent", {"maximum_mach_number": 1.}, "low-Mach"),
         ("invalid-pressure-fraction", {"maximum_pressure_fraction": 1.}, "pressure-fraction")])
    add("equipment.instrument", TransmitterEvidence,
        dict(instrument_id="p1", location_id="tank", variable=Variable("P", "pressure", "Pa", "absolute"),
             calibration_id="calibration", response_id="response", source_ids=("authored",),
             parameter_origin=Origin.SYNTHETIC),
        [("missing-pressure-reference", {"variable": Variable("P", "pressure", "Pa")}, "absolute/gauge"),
         ("missing-sensor-location", {"location_id": ""}, "location")])
    add("storage.cryo_compressed", CryoCompressedDomain,
        dict(minimum_temperature_k=15., maximum_temperature_k=400., minimum_pressure_pa_absolute=1e5,
             maximum_pressure_pa_absolute=1e8, minimum_inventory_kg=.001,
             maximum_initial_temperature_k=100., minimum_initial_pressure_to_critical_ratio=1.1,
             allowed_phases=("liquid", "supercritical"), evidence_id="authored"),
        [("critical-pressure-not-exceeded", {"minimum_initial_pressure_to_critical_ratio": .9}, "critical pressure"),
         ("unmodelled-two-phase-scope", {"allowed_phases": ("two_phase",)}, "coexistence")])
    add("storage.adsorption", AdsorptionVesselGeometry,
        dict(internal_volume_m3=1., adsorbent_mass_kg=1., solid_envelope_volume_m3=.1,
             inaccessible_volume_m3=.1, volume_basis_id="authored-volume"),
        [("negative-adsorbent-mass", {"adsorbent_mass_kg": -1.}, "adsorbent mass"),
         ("no-free-gas-volume", {"solid_envelope_volume_m3": 1.}, "free-gas volume")])
    add("storage.adsorption_thermal", BedFaceTransfers,
        dict(species=("H2", "N2"), component_mol_s=((0., 0.), (0., 0.)),
             enthalpy_w=(0., 0.), energy_reference_id="authored-reference"),
        [("bed-species-axis-mismatch", {"component_mol_s": ((0.,), (0.,))}, "matching species"),
         ("nonfinite-bed-enthalpy", {"enthalpy_w": (0., float("nan"))}, "finite")])
    add("storage.hydride_dynamic", FiniteHydrideDomain,
        dict(minimum_temperature_k=200., maximum_temperature_k=500., minimum_pressure_pa=1e4,
             maximum_pressure_pa=1e7, minimum_gas_mass_kg=1e-6),
        [("negative-bed-gas-mass-floor", {"minimum_gas_mass_kg": -1.}, "minimum_gas_mass"),
         ("inverted-bed-temperature-domain", {"maximum_temperature_k": 100.}, "bounds")])
    heat = FiniteHydrideHeatBoundary(
        "operation", 0., 10., lambda _t, _s: FiniteHydrideHeatInput(300., 0., 0.), "authored-heat")
    add("storage.hydride_compressor", HydrideCompressorStage,
        dict(stage_id="compression-stage", start_time_s=0., end_time_s=1.,
             inlet_opening_fraction=0., outlet_opening_fraction=0., bed_heat=heat,
             source_bath_temperature_k=300., receiver_bath_temperature_k=300.),
        [("invalid-bed-inlet-opening", {"inlet_opening_fraction": 1.1}, "opening fractions"),
         ("nonpositive-receiver-bath", {"receiver_bath_temperature_k": 0.}, "receiver_bath_temperature")])
    add("storage.carrier_reaction", CarrierProcessEvidence,
        dict(process_id="lohc", clock_id="operation", region_id="reactor", phase_reference_id="liquid-reference",
             extent_source_id="kinetics", thermal_boundary_id="thermal", withdrawal_assumption_id="takeoff",
             origin=Origin.SYNTHETIC),
        [("missing-carrier-phase-reference", {"phase_reference_id": ""}, "Declare"),
         ("unresolved-carrier-source", {"origin": Origin.UNRESOLVED}, "Resolve input meaning")])
    add("storage.solid_reaction", SolidReactionStep,
        dict(identifier="reaction-step", start_s=0., end_s=1., clock_id="operation",
             heat_input_j=100., temperature_bracket_k=(250., 500.), evidence_id="authored"),
        [("reversed-solid-temperature-bracket", {"temperature_bracket_k": (500., 250.)}, "bracket"),
         ("nonfinite-solid-heat", {"heat_input_j": float("inf")}, "heat")])
    add("storage.microsphere", MicrosphereDomain,
        dict(minimum_temperature_k=200., maximum_temperature_k=500., minimum_pressure_pa=1e4,
             maximum_pressure_pa=1e7, minimum_gas_inventory_mol=1e-9),
        [("negative-cavity-inventory-floor", {"minimum_gas_inventory_mol": -1.}, "minimum_gas_inventory"),
         ("inverted-cavity-pressure-envelope", {"maximum_pressure_pa": 1e3}, "bounds")])
    add("storage.underground", UndergroundDomain,
        dict(minimum_pressure_pa_absolute=1e5, maximum_pressure_pa_absolute=1e7,
             minimum_temperature_k=280., maximum_temperature_k=350.,
             maximum_water_vapor_mass_fraction=.01, evidence_id="authored"),
        [("nonpositive-cavern-pressure", {"minimum_pressure_pa_absolute": 0.}, "positive pressure"),
         ("unsupported-cold-cavern", {"minimum_temperature_k": 250.}, "273.16")])
    add("storage.porous_reservoir", PorousReservoirGeometry,
        dict(radial_faces_m=(1., 2., 3.), thickness_m=10., porosity=(.2, .2),
             permeability_m2=(1e-12, 1e-12), temperature_k=(300., 300.), evidence_id="authored"),
        [("nonphysical-unit-porosity", {"porosity": (1., .2)}, "below one"),
         ("permeability-cell-axis-mismatch", {"permeability_m2": (1e-12,)}, "cell count")])
    return tuple(cases)


CASES = _cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.family}::{c.scenario}")
def test_family_input_rejection(case, record_property):
    record_property("family", case.family)
    record_property("input_target", case.target)
    record_property("invalid_scenario", case.scenario)
    baseline = case.factory(**case.baseline)
    assert baseline is not None
    bad = {**case.baseline, **case.changes}
    with pytest.raises((ValueError, TypeError), match=case.message):
        case.factory(**bad)


@pytest.mark.parametrize("scenario,kwargs,message", [
    ("nonpositive-equilibrium-temperature", {"temperature_k": 0., "fraction": .5, "branch": "absorption"}, "temperature"),
    ("impossible-stored-fraction", {"temperature_k": 300., "fraction": 1.1, "branch": "absorption"}, "fraction"),
])
def test_hydride_equilibrium_input(scenario, kwargs, message, record_property):
    record_property("family", "storage.hydride_equilibrium")
    record_property("input_target", "VanthoffPlateau.fugacity_pa")
    record_property("invalid_scenario", scenario)
    plateau = VanthoffPlateau(30000., 100., 1e5)
    with pytest.raises(ValueError, match=message):
        plateau.fugacity_pa(**kwargs)


@pytest.mark.parametrize("scenario,pressure,temperature,message", [
    ("negative-provider-pressure", -1., 300., "pressure_pa"),
    ("nonfinite-provider-temperature", 1e5, float("nan"), "temperature_k"),
])
def test_native_property_input_preflight(scenario, pressure, temperature, message, record_property):
    record_property("family", "thermo.pure_fluid")
    record_property("input_target", "CoolPropProperties.state_pt")
    record_property("invalid_scenario", scenario)
    provider = CoolPropProperties("Hydrogen")
    with pytest.raises(ValueError, match=message):
        provider.state_pt(pressure, temperature)


def test_equipment_storage_input_manifest_is_complete():
    # Metadata invariant only; family coverage is derived from executed JUnit rows.
    families = {c.family for c in CASES} | {"storage.hydride_equilibrium"}
    assert families == set(INPUT_FAMILY_IDS)
    assert len(families) == 28
