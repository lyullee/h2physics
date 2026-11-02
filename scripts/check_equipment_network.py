"""Exercise pinned native equipment, finite phase inventory and full external ledgers.

All equipment/geometry/heat/map values below are authored synthetic inputs.
The checks establish numerical/interface behavior, not experimental qualification.
"""

import hashlib
import importlib.metadata
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_equipment import (
    Lh2dtEquipmentNetwork,
    Lh2dtSharedValve,
    stratified_node_with_heat_ledger,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.equipment import BoundaryPower
from h2physics.release import (
    HomogeneousIsentropicNozzle,
    NozzleOpening,
    SourceHistory,
    SourceLocation,
)
from h2physics.thermo import CoolPropProperties

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/native_packages"
digest = hashlib.sha256()
for file in sorted((target / "lh2dt").glob("*.py")):
    digest.update(file.name.encode())
    digest.update(file.read_bytes())
if digest.hexdigest() != "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61":
    raise SystemExit("Install/review the pinned LH2DT snapshot before running this case")
sys.path.insert(0, str(target))
from lh2dt import (  # noqa: E402
    DynamicNetworkSimulator,
    HEMPipe,
    HorizontalVesselGeometry,
    HydrogenProperties,
    MappedPump,
    Pipe,
    SteadyNetwork,
    StratifiedTank,
    StratifiedTankParameters,
    StratifiedTankState,
    Vaporizer,
    VaporizerLink,
    stratified_tank_node,
)
from lh2dt.properties import ThermoState as NativeState  # noqa: E402
from lh2dt.valve import ValveResult  # noqa: E402


@dataclass
class Case:
    network: Lh2dtEquipmentNetwork
    tank: Any
    initial: Any
    native_node: Any
    properties: Any
    heater: Any


def make_case(*, segments=128, use_low_level=True):
    direct = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    properties = (Lh2dtLowLevelProperties(direct, state_factory=NativeState) if use_low_level
                  else HydrogenProperties("ParaHydrogen"))
    bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
    network = Lh2dtEquipmentNetwork(SteadyNetwork(properties), bridge, state_factory=NativeState)
    shape = HorizontalVesselGeometry(.3, .3, .05)
    parameters = StratifiedTankParameters(1000., 1000., .1, .1, 1., 1., 100., 50., .1, .15,
                                          minimum_pressure_Pa=10000., maximum_pressure_Pa=1250000.)
    tank = StratifiedTank(shape, parameters, properties)
    liquid, vapor = properties.from_pT(300000., 20.), properties.from_pT(300000., 28.)
    liquid_mass = liquid.density_kg_m3 * shape.volume_m3 * .5
    vapor_mass = vapor.density_kg_m3 * shape.volume_m3 * .5
    initial = StratifiedTankState(liquid_mass, liquid_mass*liquid.specific_internal_energy_J_kg,
        vapor_mass, vapor_mass*vapor.specific_internal_energy_J_kg, 20., 28.)
    node = stratified_tank_node("supply", tank, initial, ambient_temperature_K=300., boundary_phase="liquid")
    network.add_boundary("supply", bridge.state_pt(300000., 20.))
    network.add_boundary("delivery", bridge.state_pt(150000., 300.))
    network.add_junction("cold", bridge.state_pt(820000., 20.1))
    network.add_junction("gas", bridge.state_pt(800000., 200.))
    pump = MappedPump([(0., 600000.), (.004, 450000.), (.008, 0.)],
        reference_speed_rpm=3000., speed_rpm=3000., isentropic_efficiency=.7,
        npsh_required_m=.5, properties=properties)
    pipe = Pipe(3., .003, 1e-6, local_loss_coefficient=2., properties=properties)
    heater = Vaporizer(25., 50000., properties, integration_segments=segments, minimum_approach_K=5.)
    heated_pipe = VaporizerLink(pipe, heater, 300., properties)
    valve = Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), bridge,
        NozzleOpening.circular("delivery-valve", .002, effective_area_factor=.8,
                              area_basis_id="synthetic-effective-area-closure"),
        result_factory=ValveResult, opening_fraction=1., allow_reverse=False)
    network.add_link("pump", "supply", "cold", pump,
        power_reader=lambda result: BoundaryPower(shaft_work_w=result.shaft_power_W),
        source_port_id="supply/out", target_port_id="pump/out")
    network.add_link("heated-pipe", "cold", "gas", heated_pipe,
        power_reader=lambda result: BoundaryPower(heat_w=result.thermal_power_W),
        source_port_id="pipe/in", target_port_id="heater/out")
    network.add_link("valve", "gas", "delivery", valve, power_reader=lambda result: BoundaryPower(),
        source_port_id="valve/in", target_port_id="delivery/in")
    return Case(network, tank, initial, node, properties, heater)


def total_energy(case, state):
    p = case.tank.parameters
    return (state.liquid_internal_energy_J + state.vapor_internal_energy_J
            + p.lower_wall_heat_capacity_J_K*state.lower_wall_temperature_K
            + p.upper_wall_heat_capacity_J_K*state.upper_wall_temperature_K)


def total_mass(state):
    return state.liquid_mass_kg + state.vapor_mass_kg


def closed_heat_check(*, bridge_heat):
    case = make_case()
    graph = SteadyNetwork(case.properties)
    graph.add_boundary("supply", case.native_node.thermo(case.initial))
    node = (stratified_node_with_heat_ledger(case.native_node) if bridge_heat else case.native_node)
    row = DynamicNetworkSimulator(graph, {"supply": node}).simulate(.1, .1)[-1]
    actual = total_energy(case, row.states["supply"]) - total_energy(case, case.initial)
    return actual-row.cumulative_boundary_energy_J["supply"]


def pipe_limits():
    properties = HydrogenProperties("ParaHydrogen")
    results = []
    liquid, vapor = properties.saturated_liquid(300000.), properties.saturated_vapor(300000.)
    mixture = properties.from_ph(300000., .8*liquid.specific_enthalpy_J_kg + .2*vapor.specific_enthalpy_J_kg)
    for name, initial, kind in (("gas", properties.from_pT(100000., 300.), Pipe),
                                ("homogeneous-mixture", mixture, HEMPipe)):
        final = properties.from_ph(initial.pressure_Pa-10., initial.specific_enthalpy_J_kg)
        raw = kind(1., .001, 0., properties=properties).evaluate(initial, final)
        viscosity = (properties.viscosity_Pa_s(initial) if name == "gas" else
                     .8*properties.viscosity_Pa_s(liquid)+.2*properties.viscosity_Pa_s(vapor))
        expected = initial.density_kg_m3*np.pi*.001**4*10./(128.*viscosity)
        error = abs(raw.mass_flow_kg_s/expected-1.)
        assert raw.reynolds_number < 2300 and error < 1e-6
        results.append((name, raw.mass_flow_kg_s, raw.reynolds_number, error))
    return results


def heater_reference(case, steady):
    inlet = steady.native.node_states["cold"]
    pressure = steady.node_states["gas"].pressure_pa
    flow = steady.native.link_flows["heated-pipe"].mass_flow_kg_s
    source_temperature = 295.  # native 300 K source minus the declared 5 K approach parameter
    initial_h = inlet.specific_enthalpy_J_kg
    reference = solve_ivp(lambda _ua, h: [(source_temperature-case.properties.from_ph(pressure, h[0]).temperature_K)/flow],
        (0., 25.), [initial_h], method="DOP853", rtol=1e-10, atol=1e-5, max_step=25/80)
    assert reference.success
    heat_reference = flow*(reference.y[0, -1]-initial_h)
    values = []
    for segments in (64, 128, 256, 512):
        model = Vaporizer(25., 50000., case.properties, integration_segments=segments, minimum_approach_K=5.)
        result = model.evaluate(inlet, pressure, flow, 300.)
        values.append((segments, result.heat_into_hydrogen_W,
                       abs(result.heat_into_hydrogen_W/heat_reference-1.)))
    assert values[-1][2] < 1e-4
    return heat_reference, values


def dynamic_case(step, *, use_low_level=True):
    case = make_case(use_low_level=use_low_level)
    stages = []
    node = stratified_node_with_heat_ledger(case.native_node)
    case.network.native.set_boundary_state("supply", node.thermo(case.initial))
    first = case.network.solve()
    start = time.perf_counter()
    trace = DynamicNetworkSimulator(case.network.checked_native(on_solve=stages.append),
                                    {"supply": node}).simulate(2., step)
    elapsed = time.perf_counter()-start
    assert len(stages) == 5*len(trace)  # exact reviewed native RK4 stage/accepted-solve contract
    delivered_mass = delivered_energy = equipment_power = 0.
    maximum_mass = maximum_energy = maximum_tank_energy = 0.
    previous = 0.
    for index, row in enumerate(trace):
        width = row.time_s-previous
        previous = row.time_s
        sampled = stages[index*5:index*5+4]
        weights = (1., 2., 2., 1.)
        delivered_mass += width/6*sum(w*s.boundary_outlet_kg_s for w, s in zip(weights, sampled, strict=True))
        delivered_energy += width/6*sum(w*s.boundary_outlet_enthalpy_w for w, s in zip(weights, sampled, strict=True))
        equipment_power += width/6*sum(w*sum(item.power.total_w for item in s.transfers)
                                        for w, s in zip(weights, sampled, strict=True))
        state = row.states["supply"]
        mass_error = total_mass(state)-total_mass(case.initial)+delivered_mass
        delta_energy = total_energy(case, state)-total_energy(case, case.initial)
        external_heat = row.cumulative_boundary_ambient_heat_J["supply"]
        energy_error = delta_energy-external_heat+delivered_energy-equipment_power
        tank_error = delta_energy-row.cumulative_boundary_energy_J["supply"]
        maximum_mass = max(maximum_mass, abs(mass_error))
        maximum_energy = max(maximum_energy, abs(energy_error))
        maximum_tank_energy = max(maximum_tank_energy, abs(tank_error))
    assert maximum_mass < 1e-8 and maximum_energy < 1e-3 and maximum_tank_energy < 1e-5
    accepted = [stages[index*5+4] for index in range(len(trace))]
    history = SourceHistory(SourceLocation("plant/delivery-valve", "synthetic-time-zero", "local-ENU",
        (3., 0., 1.), (1., 0., 0.)), (0., *(row.time_s for row in trace)),
        (first.native_component_results["valve"].nozzle,
         *(snapshot.native_component_results["valve"].nozzle for snapshot in accepted)), "window_end")
    assert len(history.samples) == len(trace)+1
    last = trace[-1]
    print(f"dynamic low_level={use_low_level}, dt={step:g}: delivered={delivered_mass:.12g} kg, "
          f"energy residual={maximum_energy:.9g} J, wall={elapsed:.6g} s", flush=True)
    return (step, delivered_mass, last.thermo_states["supply"].pressure_Pa,
            maximum_mass, maximum_energy, maximum_tank_energy, elapsed, len(stages)), last


def main():
    case = make_case()
    steady = case.network.solve()
    pipes = pipe_limits()
    heat_reference, heat_rows = heater_reference(case, steady)
    legacy_error = closed_heat_check(bridge_heat=False)
    fixed_error = closed_heat_check(bridge_heat=True)
    assert abs(legacy_error) > 1. and abs(fixed_error) < 1e-5
    print("closed ambient-heat legacy/bridged residuals", legacy_error, fixed_error, flush=True)
    # A converged hydraulic/energy point can still violate a declared NPSH requirement.
    rejected = make_case()
    rejected.network.native.links[0].component.npsh_required_m = 1000.
    inadmissible = rejected.network.solve(require_closed=False)
    assert inadmissible.native_success
    assert any("inadmissible" in message for message in inadmissible.violations(rejected.network.tolerances))
    negative_margin = inadmissible.native_component_results["pump"].cavitation_margin_m
    assert negative_margin < 0.
    rows = []
    for step in (1., .5, .25):
        result, _last = dynamic_case(step)
        rows.append(result)
    original, _last_original = dynamic_case(.5, use_low_level=False)
    provider_mass_difference = abs(original[1]-rows[1][1])/original[1]
    provider_pressure_difference = abs(original[2]-rows[1][2])/original[2]
    assert provider_mass_difference < 1e-6 and provider_pressure_difference < 1e-6
    pressure_change = abs(rows[-1][2]-rows[-2][2])/rows[-1][2]
    mass_change = abs(rows[-1][1]-rows[-2][1])/rows[-1][1]
    assert pressure_change < 1e-5 and mass_change < 1e-6
    native_pump = steady.native_component_results["pump"]
    assert native_pump.operating_point_physical_valid and native_pump.cavitation_margin_m > 0
    text = ["# Native equipment and finite-inventory network verification", "",
        f"Native lh2dt_models {importlib.metadata.version('lh2dt_models')}, public MIT revision "
        "`b2f276333c1b1793c39f25763703d196d36742ec`.",
        f"Top-level native Python-source SHA-256: `{digest.hexdigest()}`.",
        f"Declared property basis: `{case.network.bridge.basis.reference_id}` / ParaHydrogen.",
        "The main case uses the verified single-flash native property facade, with explicit "
        "1e-8 quality endpoint budget matching the reviewed native policy. A same-step "
        "original-provider trajectory is compared separately; no table/fallback is used.",
        "All geometry, map, heat and operating inputs are authored synthetic values. "
        "No field-data calibration or experimental facility qualification is claimed.", "",
        "Reproduce with `python scripts/check_equipment_network.py`. The exact optional "
        "native installation is documented in HANDOFF.md. The case factory exposes every "
        "parameter directly in Python.", "",
        "The 0.3 m diameter, 0.3 m straight-length, 0.05 m head-depth vessel has separate "
        "initial liquid/vapor half volumes at 300000 Pa, 20/28 K. Wall capacities are "
        "1000 J/K each, ambient conductances 0.1 W/K each, wall/fluid U values 1 W/(m² K), "
        "liquid/vapor interface conductances 100/50 W/K and wall axial conductance 0.1 W/K. "
        "A liquid phase port feeds the explicit 3000 rpm pressure-rise map, a 3 m × 3 mm "
        "line (roughness 1 µm, local loss 2), a 25 W/K / 50 kW-cap steady vaporizer with "
        "5 K approach parameter and a 2 mm / 0.8 effective-area shared valve. "
        "The delivery boundary sets 150000 Pa; its reservoir temperature is not substituted "
        "for the transmitted stream temperature. All fluid states use ParaHydrogen.", "",
        "| Component | Flow kg/s | Heat into fluid W | Shaft work into fluid W | "
        "Enthalpy/power residual W | Momentum residual Pa |",
        "|---|---:|---:|---:|---:|---|"]
    for item in steady.transfers:
        momentum = "unavailable" if item.momentum_residual_pa is None else f"{item.momentum_residual_pa:.12g}"
        text.append(f"| {item.component_id} | {item.mass_flow_kg_s:.12g} | {item.power.heat_w:.12g} | "
                    f"{item.power.shaft_work_w:.12g} | {item.energy_residual_w:.12g} | {momentum} |")
    text += ["", f"Native pump NPSH available/required: {native_pump.npsh_available_m:.12g} / "
             f"{native_pump.npsh_required_m:.12g} m. Map/NPSH admissibility is checked, "
             "not inferred from mathematical convergence. Missing valve momentum is retained "
             "as unavailable, not zero. Energy accounting is the native steady enthalpy-only "
             "level; finite port kinetic/potential energy is outside that ledger.", "",
             f"A second graph with a declared 1000 m NPSH requirement still mathematically "
             f"converges but has margin {negative_margin:.12g} m. Host checks reject that "
             "operating point despite closed mass/energy. This is an authored domain-failure "
             "case, not a pump degradation prediction.", "",
             "| Pipe limit | Flow kg/s | Re | Relative Poiseuille error |",
             "|---|---:|---:|---:|"]
    text += [f"| {name} | {flow:.12g} | {re:.12g} | {error:.12g} |" for name, flow, re, error in pipes]
    text += ["", "Both limits use 1 m length, 1 mm diameter and 10 Pa pressure difference. "
             "The mixture uses an explicitly declared 0.2 equilibrium quality and the native "
             "quality-weighted viscosity closure. Agreement checks the laminar limit of that "
             "closure; it does not validate two-phase slip, distributed flashing or real pipe data.", "",
             f"Independent enthalpy-coordinate DOP853 vaporizer reference heat: {heat_reference:.12g} W. "
             "It uses the same EOS and governing heat-transfer law through a different numerical "
             "integrator, not an independent physical experiment. The finest relative heat gate is 1e-4.", "",
             "| Native enthalpy segments | Heat W | Relative reference error |", "|---:|---:|---:|"]
    text += [f"| {segments} | {heat:.12g} | {error:.12g} |" for segments, heat, error in heat_rows]
    text += ["", f"A closed 0.1 s tank case exposes the original generic-network external-heat "
             f"ledger omission: residual {legacy_error:.12g} J. The explicit host heat bridge gives "
             f"{fixed_error:.12g} J while retaining identical native phase equations/advance/combine callbacks. "
             "This is request 007; the receiving repository was not edited.", "",
             "| Step s | Delivered kg over 2 s | Final tank P Pa | Maximum full mass residual kg | "
             "Maximum full energy residual J | Maximum tank energy residual J | Wall seconds | Checked solves |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    text += ["| " + " | ".join(f"{value:.12g}" for value in row) + " |" for row in rows]
    text += ["", f"At step 0.5 s the original provider takes {original[6]:.12g} s versus "
             f"{rows[1][6]:.12g} s for the single-flash facade (ratio {original[6]/rows[1][6]:.9g}). "
             f"Relative delivered-mass/final-pressure differences are {provider_mass_difference:.12g} / "
             f"{provider_pressure_difference:.12g}, each below the declared 1e-6 coupled gate. "
             "This is a measured complete solver path, not an extrapolated property-call benchmark."]
    text += ["", f"Finest-two-step relative delivered-mass/final-pressure differences: "
             f"{mass_change:.12g} / {pressure_change:.12g}; respective gates are 1e-6 / 1e-5. "
             "Every native RK stage and accepted solve passes host mass, enthalpy/power, "
             "reported momentum and declared operability checks. Only accepted points enter "
             "the predicted nozzle-plane SourceHistory; intermediate solves are diagnostic samples.", "",
             "The full external ledger combines tank inventory change, tank ambient heat, "
             "pump/vaporizer power and delivered enthalpy/mass with the reviewed native RK4 "
             "weights. Its stage grouping is pinned to this exact native simulator revision. "
             "Valve nozzle quality is not a ground fraction. Finite line inventory, water hammer, "
             "stagnant/isolation transients, dynamic vaporizer inventory, arbitrary networks and "
             "independent equipment data remain outside this verification.", "", "Host code SHA-256:", ""]
    for relative in ("src/h2physics/equipment.py", "src/h2physics/adapters/lh2dt_equipment.py",
                     "src/h2physics/adapters/lh2dt_properties.py", "src/h2physics/thermo/coolprop.py",
                     "scripts/check_equipment_network.py"):
        text.append(f"- `{relative}`: `{hashlib.sha256((root/relative).read_bytes()).hexdigest()}`")
    (root / "research/native_equipment_network.md").write_text("\n".join(text)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
