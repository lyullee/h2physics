"""Verify finite native line/vaporizer storage, command clocks and isolation."""

import hashlib
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_dynamics import (
    InventoryClosureError,
    Lh2dtDynamicEquipment,
    Lh2dtInventoryNode,
    lumped_inventory_reader,
)
from h2physics.adapters.lh2dt_equipment import Lh2dtEquipmentNetwork, Lh2dtSharedValve
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.dynamics import ScheduledEquipmentCommand
from h2physics.equipment import BoundaryPower
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties

root = Path(__file__).resolve().parents[1]
target = root / "artifacts/native_packages"
digest = hashlib.sha256()
for file in sorted((target / "lh2dt").glob("*.py")):
    digest.update(file.name.encode())
    digest.update(file.read_bytes())
if digest.hexdigest() != "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61":
    raise SystemExit("Install the exact optional native snapshot documented in HANDOFF.md")
sys.path.insert(0, str(target))
from lh2dt import (  # noqa: E402
    DynamicHEMPipe,
    DynamicNetworkSimulator,
    DynamicVaporizer,
    HEMPipe,
    SteadyNetwork,
    dynamic_hem_pipe_node,
    dynamic_vaporizer_node,
)
from lh2dt.properties import ThermoState as NativeState  # noqa: E402
from lh2dt.valve import ValveResult  # noqa: E402


def properties():
    direct = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    native = Lh2dtLowLevelProperties(direct, state_factory=NativeState)
    bridge = Lh2dtProperties(native, reference_id=direct.basis.reference_id)
    graph = Lh2dtEquipmentNetwork(SteadyNetwork(native), bridge, state_factory=NativeState)
    return direct, native, bridge, graph


def make_case(*, reverse_sealed=False):
    direct, native, bridge, graph = properties()
    line = DynamicHEMPipe(.5, .01, 1e-6, 10., fluid_wall_UA_W_K=.05,
        ambient_UA_W_K=.01, ambient_temperature_K=300., properties=native)
    heater = DynamicVaporizer(.0002, 20., .2, 300., .1, 100., native)
    line_pressure, heater_pressure = ((270000., 320000.) if reverse_sealed else (320000., 280000.))
    line_state = line.initialize(native.from_ph(line_pressure,
        direct.saturated(line_pressure, .1).enthalpy_j_kg), wall_temperature_K=30.)
    heater_state = heater.initialize(native.from_ph(heater_pressure,
        direct.saturated(heater_pressure, .2).enthalpy_j_kg), wall_temperature_K=35.)
    bindings = {
        "line": Lh2dtInventoryNode(dynamic_hem_pipe_node("line", line, line_state),
                                   lumped_inventory_reader(line.wall_heat_capacity, bridge.basis)),
        "vaporizer": Lh2dtInventoryNode(dynamic_vaporizer_node("vaporizer", heater, heater_state),
                                       lumped_inventory_reader(heater.wall_heat_capacity, bridge.basis)),
    }
    graph.add_boundary("feed", bridge.state_pt(350000., 20.))
    for name, binding in bindings.items():
        graph.native.add_boundary(name, binding.native_node.thermo(binding.native_node.initial_state))
    graph.add_boundary("delivery", bridge.state_pt(150000., 300.))

    def valve(name):
        return Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), bridge,
            NozzleOpening.circular(name, .00015, effective_area_factor=.8,
                                   area_basis_id="authored-synthetic-orifice"),
            result_factory=ValveResult, opening_fraction=0. if reverse_sealed else 1., allow_reverse=True)

    feed, outlet = valve("feed-valve"), valve("outlet-valve")
    restriction = HEMPipe(1., .0002, 1e-6, properties=native)
    for name, left, right, component in (("feed-valve", "feed", "line", feed),
            ("restriction", "line", "vaporizer", restriction),
            ("outlet-valve", "vaporizer", "delivery", outlet)):
        graph.add_link(name, left, right, component, power_reader=lambda _raw: BoundaryPower(),
                       source_port_id=name+"/in", target_port_id=name+"/out")
    return graph, bindings, feed, outlet


def total_mass(inventories):
    return sum(value.mass_kg for value in inventories.values())


def total_energy(inventories):
    return sum(value.total_energy_j for value in inventories.values())


def isolated_case(step):
    graph, bindings, feed, outlet = make_case()
    started = time.perf_counter()
    run = Lh2dtDynamicEquipment(graph, bindings, simulator_factory=DynamicNetworkSimulator).run(
        1., step, clock_id="authored-operation-zero", commands=(
            ScheduledEquipmentCommand("feed-isolation", .137, lambda _t, _g: feed.set_opening(0.)),
            ScheduledEquipmentCommand("outlet-isolation", .411, lambda _t, _g: outlet.set_opening(0.))))
    elapsed = time.perf_counter()-started
    assert [event.time_s for event in run.transitions] == [.137, .411]
    first_close = next(row for row in run.steps if row.time_s == .137)
    second_close = next(row for row in run.steps if row.time_s == .411)
    final = run.steps[-1]
    released_after_feed_isolation = total_mass(first_close.inventories)-total_mass(second_close.inventories)
    assert released_after_feed_isolation > 0.
    sealed_mass_error = abs(total_mass(final.inventories)-total_mass(second_close.inventories))
    added_heat = sum(final.balances[name].external_heat_j-second_close.balances[name].external_heat_j
                     for name in bindings)
    sealed_energy_error = abs(total_energy(final.inventories)-total_energy(second_close.inventories)-added_heat)
    assert sealed_mass_error < 1e-12 and sealed_energy_error < 1e-8 and added_heat > 0.
    for event, component in zip(run.transitions, ("feed-valve", "outlet-valve"), strict=True):
        before = next(item for item in event.before.transfers if item.component_id == component)
        after = next(item for item in event.after.transfers if item.component_id == component)
        assert before.mass_flow_kg_s > 0. and after.mass_flow_kg_s == 0.
    for row in run.steps:
        for name in bindings:
            assert 0. < row.equipment.node_states[name].vapor_mass_fraction < 1.
    maximum_mass = max(abs(b.mass_residual_kg) for row in run.steps for b in row.balances.values())
    maximum_energy = max(abs(b.energy_residual_j) for row in run.steps for b in row.balances.values())
    print(f"dt={step:g}, post-isolation discharge={released_after_feed_isolation:.12g} kg, "
          f"mass/energy residual={maximum_mass:.3g} kg / {maximum_energy:.3g} J", flush=True)
    return run, (step, len(run.steps), released_after_feed_isolation, maximum_mass, maximum_energy,
                 sealed_mass_error, sealed_energy_error, elapsed)


def analytic_heat_check():
    _direct, native, bridge, graph = properties()
    # Fluid-wall UA is zero: the wall-only relaxation has a closed-form reference.
    heater = DynamicVaporizer(.001, 2., 0., 300., 1., 100., native)
    initial = heater.initialize(native.from_pT(200000., 300.), wall_temperature_K=200.)
    observed_times = []

    def ambient(at):
        observed_times.append(at)
        return 280.+3.*at

    node = dynamic_vaporizer_node("sealed", heater, initial, ambient_temperature_K=ambient)
    graph.native.add_boundary("sealed", node.thermo(initial))
    bindings = {"sealed": Lh2dtInventoryNode(node, lumped_inventory_reader(2., bridge.basis))}
    commands = tuple(ScheduledEquipmentCommand(f"clock-check-{at}", at, lambda _t, _g: None)
                     for at in (10.37, 11.11))
    control_times = []
    run = Lh2dtDynamicEquipment(graph, bindings, simulator_factory=DynamicNetworkSimulator).run(
        2., .05, start_time_s=10., clock_id="authored-absolute-clock", commands=commands,
        continuous_command=lambda at, _graph: control_times.append(at))
    expected = 280.+3.*(12.-2.)+(200.-280.-3.*(10.-2.))*math.exp(-2./2.)
    error = abs(run.steps[-1].native.states["sealed"].wall_temperature_K-expected)
    assert error < 1e-6 and min(observed_times) == 10. and max(observed_times) == 12.
    assert control_times[0] == 10. and min(control_times) == 10. and max(control_times) == 12.
    assert run.steps[-1].inventories["sealed"].mass_kg == run.initial_inventories["sealed"].mass_kg
    assert run.steps[-1].inventories["sealed"].fluid_internal_energy_j == run.initial_inventories["sealed"].fluid_internal_energy_j
    return expected, error


def negative_checks():
    graph, bindings, _feed, _out = make_case(reverse_sealed=True)
    binding = bindings["vaporizer"]
    bindings["vaporizer"] = replace(binding, inventory_reader=lumped_inventory_reader(40., graph.bridge.basis))
    try:
        Lh2dtDynamicEquipment(graph, bindings, simulator_factory=DynamicNetworkSimulator).run(
            .1, .05, clock_id="wrong-wall-capacity")
    except InventoryClosureError as exc:
        assert "vaporizer: inventory energy" in str(exc)
        wrong_wall_residual = exc.step.balances["vaporizer"].energy_residual_j
    else:
        raise AssertionError("Incorrect wall storage was accepted")
    graph, bindings, _feed, _out = make_case()
    try:
        Lh2dtDynamicEquipment(graph, bindings, simulator_factory=DynamicNetworkSimulator).run(
            .2, .05, clock_id="forbidden-inventory-replacement", commands=(
                ScheduledEquipmentCommand("replace-fluid-state", .1,
                    lambda _t, g: g.set_boundary_state("line", g.properties.from_pT(1e6, 300.))),))
    except ValueError as exc:
        assert "replaced dynamic inventory" in str(exc)
    else:
        raise AssertionError("An equipment command overwrote a finite inventory boundary")
    return wrong_wall_residual


def unpartitioned_comparison(reference_mass):
    graph, bindings, feed, outlet = make_case()

    def commands(at, _graph):
        feed.set_opening(0. if at >= .137 else 1.)
        outlet.set_opening(0. if at >= .411 else 1.)

    raw = DynamicNetworkSimulator(graph.checked_native(),
        {name: binding.native_node for name, binding in bindings.items()},
        command_callback=commands).simulate(1., .1)
    mass = sum(bindings[name].inventory_reader(state).mass_kg for name, state in raw[-1].states.items())
    difference = mass-reference_mass
    assert abs(difference) > 1e-8
    return difference


def main():
    rows, runs = [], []
    for step in (.1, .05, .025):
        run, row = isolated_case(step)
        runs.append(run)
        rows.append(row)
    coarse, fine = runs[-2].steps[-1], runs[-1].steps[-1]
    mass_difference = max(abs(coarse.inventories[n].mass_kg/fine.inventories[n].mass_kg-1.) for n in fine.inventories)
    pressure_difference = max(abs(coarse.equipment.node_states[n].pressure_pa/fine.equipment.node_states[n].pressure_pa-1.) for n in fine.inventories)
    assert mass_difference < 1e-6 and pressure_difference < 1e-6
    reverse_graph, reverse_bindings, _feed, _out = make_case(reverse_sealed=True)
    reverse = Lh2dtDynamicEquipment(reverse_graph, reverse_bindings, simulator_factory=DynamicNetworkSimulator).run(
        .5, .025, clock_id="authored-reverse-transfer")
    assert all(next(t for t in row.equipment.transfers if t.component_id == "restriction").mass_flow_kg_s < 0.
               for row in reverse.steps)
    reverse_mass_error = abs(total_mass(reverse.steps[-1].inventories)-total_mass(reverse.initial_inventories))
    assert reverse_mass_error < 1e-12
    exact_wall, wall_error = analytic_heat_check()
    wrong_wall = negative_checks()
    unpartitioned_error = unpartitioned_comparison(total_mass(fine.inventories))
    text = ["# Native finite line/vaporizer storage and scheduled isolation", "",
        "Native lh2dt_models 0.1.2, MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`.",
        f"Top-level native Python-source SHA-256: `{digest.hexdigest()}`.",
        "Reproduce with `python scripts/check_dynamic_inventory.py` after the isolated optional install in HANDOFF.md.", "",
        "All geometry, commands and heat/hydraulic parameters below are authored synthetic inputs. "
        "This verifies native composition, clocks and conservation; no experimental qualification is inferred.", "",
        "The line is one 0.5 m by 10 mm mixed fluid volume (geometric volume), with wall capacity "
        "10 J/K and fluid/wall and ambient UAs 0.05 / 0.01 W/K. Initial fluid pressure/quality is "
        "320000 Pa / 0.1; wall temperature 30 K. The vaporizer volume is 0.0002 m3, wall capacity "
        "20 J/K, UAs 0.2 / 0.1 W/K, symmetric fluid heat cap 100 W, initial pressure/quality "
        "280000 Pa / 0.2 and wall temperature 35 K. Ambient is 300 K. A separate 1 m by 0.2 mm "
        "HEM restriction (roughness 1 micrometre) joins the volumes. These are separate physical "
        "volumes/restriction; line hydraulic half-segments are not also counted.", "",
        "A 350000 Pa, 20 K feed and 150000 Pa delivery reservoir connect through two shared "
        "0.15 mm nozzle valves with effective-area factor 0.8 and reverse flow enabled. "
        "Both use HEOS ParaHydrogen with an explicit 1e-8 endpoint-quality budget. The feed "
        "closes at 0.137 s and the outlet at 0.411 s; duration is 1 s. Prescribed commands "
        "partition native integration intervals, including partial end steps. The left and "
        "right hydraulic limits are retained separately while inventory remains continuous.", "",
        "| Nominal step s | Accepted steps | Discharge after feed closure kg | Max node mass residual kg | "
        "Max node energy residual J | Sealed assembly mass error kg | Sealed energy/heat error J | Wall s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    text += ["| " + " | ".join(f"{value:.12g}" for value in row) + " |" for row in rows]
    text += ["", f"Finest-two-run maximum relative final node mass/pressure differences: "
        f"{mass_difference:.12g} / {pressure_difference:.12g}; each gate is 1e-6. "
        "Mass/energy gate defaults are 1e-8 kg / 1e-4 J with relative 1e-8 on changes/fluxes, "
        "not absolute reference energy. Every node is checked separately; cancelling errors "
        "cannot pass through a global sum. All accepted fluid states remain mixed-phase in this case.", "",
        f"Evaluating the same discontinuous controls inside unsplit 0.1 s RK steps changes "
        f"final assembly mass by {unpartitioned_error:.12g} kg relative to the finest partitioned run. "
        "That trajectory can still conserve its computed fluxes. Conservation alone therefore "
        "does not verify the intended command time; the partitioned driver preserves both.", "",
        f"A reversed sealed pair (270000 / 320000 Pa) transfers mass from vaporizer to line; "
        f"assembly mass change is {reverse_mass_error:.12g} kg. Each native stage retains the actual "
        "upstream enthalpy and passes the independent steady transfer checks.", "",
        "A separate closed warm-fluid vaporizer has zero fluid/wall UA, wall C=2 J/K, ambient UA=1 W/K, "
        "initial wall 200 K and ambient 280+3*t K. Its absolute clock runs from 10 to 12 s and is "
        "partitioned at 10.37/11.11 s. The unchanged fluid mass/energy and the analytic wall ODE "
        "provide an independent limit, including time-varying ambient callback clock translation.",
        f"Analytic final wall temperature is {exact_wall:.12g} K; native absolute error is "
        f"{wall_error:.12g} K against a 1e-6 K gate.", "",
        f"Negative checks reject a doubled vaporizer wall-capacity reader (first energy residual "
        f"{wrong_wall:.12g} J) and a command that replaces a dynamic fluid boundary. "
        "The driver also requires an explicit external-heat field and matches accepted native "
        "solutions by object identity; no five-solves-per-step assumption is required.", "",
        "One cell per device assumes homogeneous equilibrium and instantaneous mixing; "
        "slip, wave propagation, finite valve motion, pressure-trigger localization, complete "
        "mass/phase depletion, frost, pump startup and independent apparatus data remain open. "
        "A closed outlet is not an empty inventory and nozzle liquid is not ground-reaching liquid.", "",
        "Host code SHA-256:", ""]
    for relative in ("src/h2physics/dynamics.py", "src/h2physics/adapters/lh2dt_dynamics.py",
                     "src/h2physics/adapters/lh2dt_equipment.py", "scripts/check_dynamic_inventory.py"):
        text.append(f"- `{relative}`: `{hashlib.sha256((root/relative).read_bytes()).hexdigest()}`")
    (root / "research/native_dynamic_inventory.md").write_text("\n".join(text)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
