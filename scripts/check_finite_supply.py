"""Verify a finite native tank/pump/line/vaporizer assembly and external ledgers."""

import hashlib
import importlib.metadata
import time
from pathlib import Path

import numpy as np
from check_equipment_network import digest, root
from check_equipment_network import make_case as reservoir_case

from h2physics.adapters.lh2dt_dynamics import integrate_equipment_rate
from h2physics.adapters.lh2dt_equipment import EquipmentClosureError, Lh2dtSharedValve
from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
from h2physics.adapters.lh2dt_supply import assemble_lh2dt_supply
from h2physics.dynamics import ScheduledEquipmentCommand
from h2physics.equipment import BoundaryPower
from h2physics.hydraulics import HydraulicConvergenceError, solve_darcy_flow
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties

NATIVE_SOURCE_HASH = digest.hexdigest()  # The helper selected the reviewed isolated native path.
import fluids.friction as friction_module  # noqa: E402
import lh2dt as native_api  # noqa: E402
from fluids.friction import Churchill_1977  # noqa: E402
from lh2dt.pipe import PipeResult  # noqa: E402
from lh2dt.properties import ThermoState as NativeState  # noqa: E402
from lh2dt.valve import ValveResult  # noqa: E402


def make_supply(*, use_low_level=True, line_pressure_pa=850000., invalid_power=False,
                use_native_restriction=False):
    # Reuse the separately recorded synthetic reservoir, phase state and pump map.
    reservoir = reservoir_case(use_low_level=use_low_level)
    props, bridge = reservoir.properties, reservoir.network.bridge
    direct = props.provider if use_low_level else CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    line = native_api.DynamicHEMPipe(5., .025, 1e-6, 100., fluid_wall_UA_W_K=.5,
        ambient_UA_W_K=.05, ambient_temperature_K=300., properties=props)
    vaporizer = native_api.DynamicVaporizer(.0002, 200., 10., 300., 1., 1000., props)
    initial_line = line.initialize(props.from_pT(line_pressure_pa, 20.1), wall_temperature_K=30.)
    initial_vaporizer = vaporizer.initialize(props.from_ph(700000.,
        direct.saturated(700000., .2).enthalpy_j_kg), wall_temperature_K=100.)

    def valve(name, opening):
        return Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), bridge,
            NozzleOpening.circular(name, .0005, effective_area_factor=.8,
                                   area_basis_id="authored-synthetic-orifice"),
            result_factory=ValveResult, opening_fraction=opening, allow_reverse=False)

    native_restriction = native_api.HEMPipe(1., .001, 1e-6, properties=props)
    restriction = native_restriction if use_native_restriction else Lh2dtDarcyPipe(
        native_restriction, bridge, viscosity_reader=native_restriction._effective_viscosity,
        friction_law=Churchill_1977, friction_law_id="fluids:Churchill_1977:Darcy",
        result_factory=PipeResult)
    return assemble_lh2dt_supply(bridge, native_api=native_api, state_factory=NativeState,
        tank=reservoir.tank, initial_tank=reservoir.initial, line=line, initial_line=initial_line,
        vaporizer=vaporizer, initial_vaporizer=initial_vaporizer,
        pump=reservoir.network.native.links[0].component,
        isolated_pump_component=valve("isolated-pump", 0.),
        restriction=restriction,
        outlet=valve("outlet-valve", 1.), delivery_state=bridge.state_pt(150000., 300.),
        power_readers={
            "running_pump": (lambda _result: BoundaryPower()) if invalid_power else
                (lambda result: BoundaryPower(shaft_work_w=result.shaft_power_W)),
            "isolated_pump": lambda _result: BoundaryPower(),
            "restriction": lambda _result: BoundaryPower(),
            "outlet": lambda _result: BoundaryPower(),
        }, tank_ambient_temperature_k=300.)


def inventory_mass(values):
    return sum(item.mass_kg for item in values.values())


def inventory_energy(values):
    return sum(item.total_energy_j for item in values.values())


def transfer(snapshot, name):
    return next(item for item in snapshot.transfers if item.component_id == name)


def ambient_power(assembly, states):
    ids, models = assembly.node_ids, assembly.native_models
    tank, line, heater = models["tank"], models["line"], models["vaporizer"]
    tank_state, line_state, heater_state = (states[ids[name]] for name in ("tank", "line", "vaporizer"))
    params = tank.parameters
    return (params.lower_ambient_UA_W_K*(300.-tank_state.lower_wall_temperature_K)
            + params.upper_ambient_UA_W_K*(300.-tank_state.upper_wall_temperature_K)
            + line.ambient_UA*(line.ambient_temperature-line_state.wall_temperature_K)
            + heater.ambient_UA*(heater.ambient_temperature-heater_state.wall_temperature_K))


def run_case(step, *, use_low_level=True):
    assembly = make_supply(use_low_level=use_low_level)
    commands = (
        ScheduledEquipmentCommand("pump-and-feed-isolation", .037,
                                  lambda _at, _graph: assembly.pump.set_mode("isolated")),
        ScheduledEquipmentCommand("outlet-isolation", .073,
                                  lambda _at, _graph: assembly.outlet.set_opening(0.)),
    )
    started = time.perf_counter()
    run = assembly.driver.run(.15, step, clock_id="authored-finite-supply-zero", commands=commands)
    elapsed = time.perf_counter()-started
    final = run.steps[-1]
    mass = integrate_equipment_rate(run, lambda snapshot: transfer(snapshot, "outlet-valve").mass_flow_kg_s,
                                    rate_unit="kg/s", integral_unit="kg")
    enthalpy = integrate_equipment_rate(run, lambda snapshot: transfer(snapshot, "outlet-valve").outlet_enthalpy_flow_w,
                                       rate_unit="W", integral_unit="J")
    shaft = integrate_equipment_rate(run, lambda snapshot: sum(item.power.shaft_work_w for item in snapshot.transfers),
                                    rate_unit="W", integral_unit="J")
    initial_states = {name: binding.native_node.initial_state for name, binding in assembly.driver.nodes.items()}
    clocks = [run.start_time_s, *(row.time_s for row in run.steps)]
    heat_values = [ambient_power(assembly, initial_states),
                   *(ambient_power(assembly, row.native.states) for row in run.steps)]
    ambient = float(np.trapezoid(heat_values, clocks))
    mass_change = inventory_mass(final.inventories)-inventory_mass(run.initial_inventories)
    energy_change = inventory_energy(final.inventories)-inventory_energy(run.initial_inventories)
    external_mass_error = mass_change+mass.value
    external_energy_error = energy_change-ambient-shaft.value+enthalpy.value
    integrated_native_mass = sum(balance.boundary_mass_kg for balance in final.balances.values())
    integrated_native_energy = sum(balance.boundary_energy_j for balance in final.balances.values())
    # Declared independent sampled-quadrature gates; tighter native per-node checks still apply.
    assert abs(external_mass_error) < 1e-8 and abs(external_energy_error) < .01
    assert abs(mass_change-integrated_native_mass) < 1e-12
    assert abs(energy_change-integrated_native_energy) < 1e-7
    first_close = next(row for row in run.steps if row.time_s == .037)
    second_close = next(row for row in run.steps if row.time_s == .073)
    residual_release = inventory_mass(first_close.inventories)-inventory_mass(second_close.inventories)
    assert residual_release > 0.
    assert abs(inventory_mass(final.inventories)-inventory_mass(second_close.inventories)) < 1e-12
    ids = assembly.node_ids
    assert abs(final.inventories[ids["tank"]].mass_kg-first_close.inventories[ids["tank"]].mass_kg) < 1e-12
    final_heat = sum(balance.external_heat_j for balance in final.balances.values())
    close_heat = sum(balance.external_heat_j for balance in second_close.balances.values())
    assert abs(inventory_energy(final.inventories)-inventory_energy(second_close.inventories)
               -final_heat+close_heat) < 1e-7
    running = [run.initial_equipment, *(row.equipment for row in run.steps)]
    pump_results = [snap.native_component_results["pump-assembly"] for snap in running
                    if snap.native_component_results["pump-assembly"].mode_id == "running"]
    minimum_npsh = min(item.native.cavitation_margin_m for item in pump_results)
    assert minimum_npsh > 0.
    for row in run.steps:
        mode = row.equipment.native_component_results["pump-assembly"].mode_id
        if row.time_s > .037:
            assert mode == "isolated" and transfer(row.equipment, "pump-assembly").power.total_w == 0.
        assert row.inventories[ids["tank"]].mass_kg > 0.
    print(f"finite supply fast={use_low_level}, dt={step:g}: delivered={mass.value:.12g} kg, "
          f"sampled external residual={external_mass_error:.3g} kg / {external_energy_error:.3g} J, "
          f"wall={elapsed:.6g} s", flush=True)
    maximum_mass = max(abs(b.mass_residual_kg) for row in run.steps for b in row.balances.values())
    maximum_energy = max(abs(b.energy_residual_j) for row in run.steps for b in row.balances.values())
    return run, (step, len(run.steps), mass.value, shaft.value, ambient, external_mass_error,
                  external_energy_error, maximum_mass, maximum_energy, residual_release, elapsed), minimum_npsh


def negative_checks():
    wrong = make_supply(invalid_power=True)
    try:
        wrong.network.solve()
    except EquipmentClosureError as exc:
        power_error = transfer(exc.snapshot, "pump-assembly").energy_residual_w
        assert abs(power_error) > 1.
    else:
        raise AssertionError("An undeclared running pump work term was accepted")
    outside = make_supply(line_pressure_pa=950000.)
    try:
        outside.network.solve()
    except EquipmentClosureError as exc:
        assert "inadmissible" in str(exc) and outside.pump.mode_id == "running"
        map_residual = transfer(exc.snapshot, "pump-assembly").momentum_residual_pa
        assert abs(map_residual) > 1000.
    else:
        raise AssertionError("An invalid map point selected isolation implicitly")
    running = outside.native_models["running_pump"]
    original_speed = running.speed_rpm
    try:
        running.set_speed_rpm(0.)
    except ValueError:
        assert running.speed_rpm == original_speed
    else:
        raise AssertionError("The reviewed stopped-machine capability has changed; review request 008")
    return power_error, map_residual


def restriction_regression():
    assembly = make_supply()
    props = assembly.network.bridge.native
    corrected = assembly.native_models["restriction"]
    legacy = corrected.native_pipe
    # Retained model-generated state from the earlier native 1 s heating trajectory.
    left = props.from_prho(820206.1092360109, 71.97923609619494)
    right = props.from_prho(819947.6847660368, 27.69354626133448)
    old, new = legacy.evaluate(left, right), corrected.evaluate(left, right)
    area = np.pi*legacy.diameter**2/4.

    def residual(result):
        speed = abs(result.mass_flow_kg_s)/(left.density_kg_m3*area)
        drop = (result.darcy_friction_factor*legacy.length/legacy.diameter+legacy.local_k)*left.density_kg_m3*speed**2/2.
        return left.pressure_Pa-right.pressure_Pa-drop

    old_error, new_error = residual(old), residual(new)
    assert abs(old.momentum_residual_Pa) < 1e-6 and abs(old_error) > 1. and abs(new_error) < .01
    try:
        solve_darcy_flow(corrected.geometry, density_kg_m3=left.density_kg_m3,
            viscosity_pa_s=legacy._effective_viscosity(left),
            driving_pressure_pa=left.pressure_Pa-right.pressure_Pa, friction_law=legacy._friction_factor)
    except HydraulicConvergenceError as exc:
        assert exc.result.root_converged
        discontinuity_residual = exc.result.momentum_residual_pa
    else:
        raise AssertionError("The retained native discontinuous-friction gap unexpectedly has a closed root")
    return old.reynolds_number, old.momentum_residual_Pa, old_error, new_error, discontinuity_residual


def long_heating_case(step):
    assembly = make_supply()
    next_notice = .25

    def progress(at, _graph):
        nonlocal next_notice
        if at >= next_notice:
            print(f"long heating dt={step:g}, native stage clock={at:.4g} s", flush=True)
            next_notice += .25

    started = time.perf_counter()
    run = assembly.driver.run(1., step, clock_id="authored-long-isolated-heating",
        commands=(ScheduledEquipmentCommand("feed-isolation", .037,
            lambda _at, _graph: assembly.pump.set_mode("isolated")),
            ScheduledEquipmentCommand("outlet-isolation", .073,
            lambda _at, _graph: assembly.outlet.set_opening(0.))), continuous_command=progress)
    closed = next(row for row in run.steps if row.time_s == .073)
    final = run.steps[-1]
    mass_error = abs(inventory_mass(final.inventories)-inventory_mass(closed.inventories))
    heat = sum(final.balances[name].external_heat_j-closed.balances[name].external_heat_j
               for name in final.inventories)
    energy_error = abs(inventory_energy(final.inventories)-inventory_energy(closed.inventories)-heat)
    flows = [transfer(row.equipment, "restriction").mass_flow_kg_s for row in run.steps]
    assert mass_error < 1e-12 and energy_error < 1e-7
    assert min(flows) < 0. < max(flows)
    maximum_node_energy = max(abs(balance.energy_residual_j) for row in run.steps for balance in row.balances.values())
    restriction = assembly.native_models["restriction"]
    assert restriction.dz == 0.  # This independent relation is for the declared horizontal restriction.
    maximum_darcy_error = 0.
    area = np.pi*restriction.diameter**2/4.
    for point in run.steps:
        item = transfer(point.equipment, "restriction")
        raw = point.equipment.native_component_results["restriction"]
        upstream = point.equipment.node_states[item.upstream_node or assembly.node_ids["line"]]
        velocity = abs(item.mass_flow_kg_s)/(upstream.density_kg_m3*area)
        recomputed = (raw.darcy_friction_factor*restriction.length/restriction.diameter
                      + restriction.local_k)*upstream.density_kg_m3*velocity**2/2.
        actual = abs(point.equipment.node_states[item.left_node].pressure_pa
                     - point.equipment.node_states[item.right_node].pressure_pa)
        maximum_darcy_error = max(maximum_darcy_error, abs(actual-recomputed))
    assert maximum_darcy_error < .01
    row = (step, len(run.steps), min(flows), max(flows), mass_error, energy_error,
           maximum_node_energy, maximum_darcy_error, time.perf_counter()-started)
    ids = tuple(final.inventories)
    profile = np.array([[point.time_s, *(point.inventories[name].mass_kg for name in ids),
                         *(point.equipment.node_states[name].pressure_pa for name in ids)]
                        for point in run.steps])
    core = hashlib.sha256()
    for relative in ("src/h2physics/dynamics.py", "src/h2physics/adapters/lh2dt_dynamics.py",
                     "src/h2physics/adapters/lh2dt_modes.py", "src/h2physics/adapters/lh2dt_supply.py",
                     "src/h2physics/hydraulics.py", "src/h2physics/adapters/lh2dt_hydraulics.py"):
        core.update((root/relative).read_bytes())
    np.savez(root / f"artifacts/finite_supply_bracketed_{step:g}.npz", profile=profile,
             node_ids=np.array(ids), row=np.array(row), core_sha256=np.array(core.hexdigest()))
    print("long final mass/pressure", profile[-1].tolist(), flush=True)
    print(f"long heating dt={step:g} passed; reversed internal transfer retained", flush=True)
    return run, row


def final_difference(first, second):
    first, second = first.steps[-1], second.steps[-1]
    mass = max(abs(first.inventories[name].mass_kg/second.inventories[name].mass_kg-1.)
               for name in first.inventories)
    pressure = max(abs(first.equipment.node_states[name].pressure_pa/second.equipment.node_states[name].pressure_pa-1.)
                   for name in first.inventories)
    return mass, pressure


def main():
    runs, rows, margins = [], [], []
    for step in (.01, .005, .0025):
        run, row, margin = run_case(step)
        runs.append(run)
        rows.append(row)
        margins.append(margin)
    refined = final_difference(runs[-2], runs[-1])
    assert max(refined) < 1e-6
    assert abs(rows[-1][5]) < abs(rows[-2][5]) < abs(rows[0][5])
    assert abs(rows[-1][6]) < abs(rows[-2][6]) < abs(rows[0][6])
    original, original_row, _margin = run_case(.005, use_low_level=False)
    compared = final_difference(runs[1], original)
    assert max(compared) < 1e-6
    wrong_work, invalid_map = negative_checks()
    old_reynolds, reported_momentum, old_darcy, new_darcy, discontinuity = restriction_regression()
    long_runs, long_rows = [], []
    for step in (.00125, .000625):
        long_run, long_row = long_heating_case(step)
        long_runs.append(long_run)
        long_rows.append(long_row)
    long_difference = final_difference(*long_runs)
    print("long-pair final mass/pressure difference", long_difference, flush=True)
    assert max(long_difference) < 1e-6
    text = ["# Finite phase-resolved supply assembly verification", "",
        "Native lh2dt_models 0.1.2, MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`.",
        f"Top-level native Python-source SHA-256: `{NATIVE_SOURCE_HASH}`.",
        "Reproduce with `python scripts/check_finite_supply.py` after the optional isolated installation in HANDOFF.md.", "",
        "The public Python assembly builder receives actual native models, initial states, factories and "
        "separate branch power readers. All inputs here are authored synthetic values; no experimental "
        "facility qualification or manufacturer map is claimed. HEOS ParaHydrogen is used throughout.", "",
        "The finite reservoir reuses the tank/phase/wall initial state and 3000 rpm map in "
        "`scripts/check_equipment_network.py`: D=0.3 m, straight length 0.3 m, head depth 0.05 m; "
        "half liquid/vapor volumes at common 300000 Pa and 20/28 K; walls 20/28 K; wall capacities "
        "1000 J/K each. Ambient UAs 0.1 W/K each, wall/fluid U=1 W/(m2 K), liquid/vapor interface "
        "UAs=100/50 W/K, wall axial UA=0.1 W/K and wall split height=0.15 m. The native pressure "
        "domain is 10000–1250000 Pa. Authored map points (kg/s, Pa rise) are (0,600000), "
        "(0.004,450000), (0.008,0), efficiency 0.7 and required NPSH 0.5 m.", "",
        "The line is a 5 m by 25 mm mixed volume with roughness 1 micrometre, wall C=100 J/K, "
        "fluid/wall UA=0.5 W/K and ambient UA=0.05 W/K. Initially 850000 Pa, 20.1 K; wall 30 K. "
        "The vaporizer volume is 0.0002 m3, wall C=200 J/K, fluid/wall UA=10 W/K, ambient UA=1 W/K, "
        "symmetric fluid heat cap=1000 W; initially 700000 Pa / quality 0.2 with wall 100 K. "
        "Ambient is 300 K. The separate 1 m by 1 mm HEM restriction has 1 micrometre roughness; "
        "line hydraulic half-segments are not also counted. The outlet shared nozzle is 0.5 mm "
        "with area factor 0.8 into a 150000 Pa reservoir. Reverse valve flow is disabled.", "",
        "At 0.037 s the pump assembly switches from the actual mapped pump to an actual closed "
        "shared valve; at 0.073 s the outlet closes. Duration=0.15 s. The first switch is a "
        "declared ideal instantaneous stop/isolation limit. It does not model rotor rundown, "
        "deadhead heating, casing fluid storage or motor losses. A native failure cannot select "
        "this mode automatically. The exact property paths use explicit 1e-8 quality roundoff budgets.", "",
        f"The restriction now uses one bracketed Darcy kernel and the explicitly selected direct "
        f"fluids {importlib.metadata.version('fluids')} Churchill_1977 Darcy function; native HEM "
        "phase-weighted viscosity is retained. This is a declared friction-correlation change, "
        "not an assertion of improved experimental accuracy in transitional two-phase flow.",
        f"Installed friction-module SHA-256: `{hashlib.sha256(Path(friction_module.__file__).read_bytes()).hexdigest()}`.", "",
        f"A retained native heating state has Re={old_reynolds:.12g}: the original reported "
        f"momentum residual is {reported_momentum:.12g} Pa but independent Darcy reconstruction "
        f"gives {old_darcy:.12g} Pa. Merely bracketing the original discontinuous friction law "
        f"still leaves {discontinuity:.12g} Pa and is rejected despite its root flag. The explicitly "
        f"selected continuous law plus bracketed solver gives {new_darcy:.12g} Pa. These distinguish "
        "numerical convergence from the empirical closure choice; request 009 specifies consolidation.", "",
        "| Step s | Accepted | Sampled delivered kg | Sampled shaft J | Sampled ambient J | "
        "External mass residual kg | External energy residual J | Max node mass residual kg | "
        "Max node energy residual J | Release after feed isolation kg | Wall s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    text += ["| " + " | ".join(f"{value:.12g}" for value in row) + " |" for row in rows]
    text += ["", "The independent external comparison uses accepted-sample trapezoids for delivery "
        "mass/enthalpy and shaft work, preserving both command limits. Ambient power is independently "
        "recomputed from each actual wall temperature and its declared ambient UA, not read from "
        "the native derivative. Gates are 1e-8 kg / 0.01 J; quadrature errors decrease under refinement. "
        "Native per-node conservation uses the native integrated fluxes separately, with the driver "
        "defaults 1e-8 kg / 1e-4 J plus relative 1e-8 on changes/fluxes. It is not a second exact "
        "RK ledger or independent physical experiment.", "",
        f"Finest-two-run maximum final node mass/pressure relative differences: {refined[0]:.12g} / "
        f"{refined[1]:.12g}; gates 1e-6 each. Minimum declared pump NPSH margin: {min(margins):.12g} m.", "",
        "After feed isolation the tank's total mass remains constant while its phases and walls "
        "continue relaxing. The stored downstream devices still discharge until outlet closure. "
        "After both outside transfers stop, the complete assembly retains mass and its stored "
        "energy change equals external ambient heat. Each dynamic node closes independently.", "",
        f"The original property path at 0.005 s takes {original_row[-1]:.12g} s versus "
        f"{rows[1][-1]:.12g} s for the single-flash facade (ratio {original_row[-1]/rows[1][-1]:.9g}). "
        f"Maximum final node mass/pressure differences are {compared[0]:.12g} / {compared[1]:.12g}, "
        "below the predeclared 1e-6 gates. This is a separate complete workload from earlier timings.", "",
        f"Negative checks reject omission of pump shaft work (residual {wrong_work:.12g} W) and "
        f"an out-of-map point (momentum residual {invalid_map:.12g} Pa). The branch remains running "
        "on failure; no implicit isolation, clipped storage or alternate property solver is selected.", "",
        "## Longer isolated heating and reverse transfer", "",
        "The unchanged assembly is also advanced to 1 s at two steps, retaining the same "
        "0.037/0.073 s commands. Heating eventually reverses the internal restriction flow; "
        "the outer ports remain closed. This checks beyond the short positive-pressure-gradient "
        "sequence. Only the single-flash path is used for this longer refinement pair.", "",
        "| Step s | Accepted | Minimum internal flow kg/s | Maximum internal flow kg/s | "
        "Closed mass error kg | Closed energy/heat error J | Max node energy residual J | "
        "Independent Darcy residual Pa | Wall s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    text += ["| " + " | ".join(f"{value:.12g}" for value in row) + " |" for row in long_rows]
    text += ["", f"Long-pair maximum relative final node mass/pressure differences: "
        f"{long_difference[0]:.12g} / {long_difference[1]:.12g}; gates 1e-6 each. "
        "An initial native 0.0025/0.00125 s pair conserved inventory but failed the final-state "
        "gate. Its tighter pair passed that gate but a newly sampled transition point failed "
        "the independent Darcy check; both negative results prompted the explicit hydraulic "
        "correction above. All gates are retained for the corrected trajectory. The horizontal Darcy pressure "
        "loss is independently recomputed from actual signed mass flow, upstream density and "
        "reported friction at accepted points; its gate is 0.01 Pa. "
        "The native zero-speed setter is also checked to reject zero while retaining its prior "
        "speed, documenting the concrete request 008 limitation.", "",
        "Independent equipment/plant experiments, wave/spatial refinement, pressure-trigger "
        "localization, phase/mass depletion, real actuator/rotor/casing dynamics, frosting and "
        "atmospheric/ground source partition remain unfinished. Results describe the declared "
        "mixed-volume and quasi-steady transfer level only.", "", "Host code SHA-256:", ""]
    for relative in ("src/h2physics/dynamics.py", "src/h2physics/adapters/lh2dt_dynamics.py",
                     "src/h2physics/adapters/lh2dt_modes.py", "src/h2physics/adapters/lh2dt_supply.py",
                     "src/h2physics/hydraulics.py", "src/h2physics/adapters/lh2dt_hydraulics.py",
                     "scripts/check_equipment_network.py", "scripts/check_finite_supply.py"):
        text.append(f"- `{relative}`: `{hashlib.sha256((root/relative).read_bytes()).hexdigest()}`")
    (root / "research/native_finite_supply.md").write_text("\n".join(text)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
