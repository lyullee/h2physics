"""Verify actual native insulation paths and layered-tank energy boundaries."""

import argparse
import hashlib
import importlib
import math
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from h2physics.adapters.lh2dt_insulation import (
    InsulationEvidence,
    Lh2dtVacuumInsulation,
    WallHeatAllocation,
    layered_inventory_reader,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.core import Origin
from h2physics.dynamics import InventoryBalance, InventoryTolerances
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
REVISION = "b2f276333c1b1793c39f25763703d196d36742ec"
NATIVE_SHA = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = ("src/h2physics/adapters/lh2dt_insulation.py", "tests/test_lh2dt_insulation.py",
              "scripts/check_insulation_integration.py")
SIGMA = 5.670374419e-8  # Independent 2022 CODATA/NIST reference for verification only.


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sha(target):
    digest = hashlib.sha256()
    for path in sorted((target / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def evidence(geometry="authored geometric warm-reference area"):
    return InsulationEvidence(geometry, "authored synthetic emissivity/construction conductances",
        "helium; coefficient synthetic, no measured accommodation inferred",
        "authored absolute annulus pressure and molecular-flow test limit",
        ("authored synthetic verification parameters", f"lh2dt_models@{REVISION}"), Origin.SYNTHETIC)


def static_checks(vacuum, pipe_module):
    parameters = vacuum.VacuumInsulationParameters(2.4, .0033, .008, .002, .025, .08,
        (vacuum.LocalizedHeatPath("neck", .0014), vacuum.LocalizedHeatPath("instrument", .0006)))
    native = vacuum.VacuumInsulation(parameters)
    boundary = Lh2dtVacuumInsulation(native, evidence=evidence())
    base = boundary.evaluate(295., 24., .006)
    expected_radiation = SIGMA * 2.4 * .0033 * (295.**4 - 24.**4)
    radiation_error = abs(dict(base.path_heat_w)["radiation"] - expected_radiation)
    assert radiation_error < 1e-12
    zero = boundary.evaluate(45., 45., .006)
    assert zero.power.heat_w == 0. and all(value == 0. for _, value in zero.path_heat_w)
    reverse = boundary.evaluate(24., 295., .006)
    assert abs(reverse.power.heat_w + base.power.heat_w) < 1e-12
    radiation_native = vacuum.VacuumInsulation(replace(parameters,
        mli_solid_conductance_W_K=0., support_conductance_W_K=0.,
        residual_gas_coefficient_W_m2K_Pa=0., localized_heat_paths=()))
    radiation_only = Lh2dtVacuumInsulation(radiation_native, evidence=evidence())
    nonlinear_ratio = radiation_only.evaluate(300., 80., 0.).power.heat_w / radiation_only.evaluate(150., 40., 0.).power.heat_w
    assert abs(nonlinear_ratio - 16.) < 1e-12
    gas_boundary = Lh2dtVacuumInsulation(vacuum.VacuumInsulation(replace(parameters,
        effective_emissivity=0., mli_solid_conductance_W_K=0., support_conductance_W_K=0.,
        localized_heat_paths=())), evidence=evidence())
    gas_rows = []
    for pressure in (0., 1e-9, 1e-6, .001, .08):
        output = gas_boundary.evaluate(295., 24., pressure)
        expected = .025 * 2.4 * pressure * (295. - 24.)
        assert abs(output.power.heat_w - expected) < 1e-12
        gas_rows.append((pressure, output.power.heat_w))
    allocation = WallHeatAllocation(("lower", "middle", "upper"), (.2, .3, .5),
        {"neck": (0., 0., 1.), "instrument": (.4, .5, .1)}, "authored area and discrete bridge fractions")
    uniform = boundary.partition(295., (24., 24., 24.), .006, allocation=allocation)
    assert abs(uniform.power.heat_w - base.power.heat_w) < 1e-12
    walls = (22., 31., 57.)
    heterogeneous = boundary.partition(295., walls, .006, allocation=allocation)
    expected = []
    for index, (fraction, cold) in enumerate(zip(allocation.area_fractions, walls, strict=True)):
        distributed = (SIGMA * 2.4 * .0033 * fraction * (295.**4 - cold**4)
            + (.008 + .002 + .025 * 2.4 * .006) * fraction * (295. - cold))
        local_conductance = (.0014 * allocation.localized_path_fractions["neck"][index]
            + .0006 * allocation.localized_path_fractions["instrument"][index])
        expected.append(distributed + local_conductance * (295. - cold))
    partition_error = max(abs(a - b) for a, b in zip(heterogeneous.zone_heat_w, expected, strict=True))
    assert partition_error < 1e-12
    failures = []
    for label, operation in (
        ("pressure above explicit molecular-flow bound", lambda: boundary.evaluate(295., 24., .080001)),
        ("unallocated native penetration", lambda: boundary.partition(295., walls, .006,
            allocation=replace(allocation, localized_path_fractions={}))),
        ("native zero-area-zone incompatibility", lambda: native.layered_wall_heat_distribution(
            295., (24., 24.), .006, area_fractions=(1., 0.),
            localized_path_fractions={"neck": (1., 0.), "instrument": (1., 0.)}))):
        try:
            operation()
        except ValueError as error:
            failures.append((label, str(error)))
        else:
            raise AssertionError(f"Negative scientific case accepted: {label}")
    envelope = pipe_module.VacuumJacketedPipeEnvelope(1.3, .018, .022, .060)
    pipe_native = envelope.make_insulation(effective_emissivity=.003,
        mli_solid_conductance_W_K=.002, support_conductance_W_K=.001,
        residual_gas_coefficient_W_m2K_Pa=.025, maximum_valid_vacuum_pressure_Pa=.08,
        localized_heat_paths=(vacuum.LocalizedHeatPath("end-bridge", .0005),))
    pipe_boundary = Lh2dtVacuumInsulation(pipe_native,
        evidence=evidence("native envelope: L=1.3 m, bore/outer/jacket-inner diameters .018/.022/.060 m"))
    assert abs(envelope.fluid_volume_m3 - math.pi / 4. * .018**2 * 1.3) < 1e-15
    assert abs(envelope.process_wall_volume_m3 - math.pi / 4. * (.022**2 - .018**2) * 1.3) < 1e-15
    assert abs(pipe_boundary.area_m2 - math.pi * .060 * 1.3) < 1e-15
    pipe_heat = pipe_boundary.evaluate(295., 24., .006)
    return parameters, base, gas_rows, uniform, heterogeneous, radiation_error, partition_error, nonlinear_ratio, failures, envelope, pipe_heat


def make_tank(native_modules, *, wall_only=False):
    vacuum, tank_module, geometry, native_properties = native_modules
    direct = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    # LayeredTank requires derivatives outside the separately tested low-level
    # facade subset. Select the complete original native property implementation.
    properties = native_properties.HydrogenProperties("ParaHydrogen")
    native_liquid = properties.saturated_liquid(200_000.)
    assert abs(native_liquid.specific_enthalpy_J_kg - direct.saturated(200_000., 0.).enthalpy_j_kg) < 1e-8
    shape = geometry.HorizontalVesselGeometry(.5, .9, .1)
    parameters = tank_module.LayeredTankParameters(liquid_cell_count=1, vapor_cell_count=1,
        wall_node_count=3, wall_heat_capacity_J_K=500., ambient_UA_W_K=0.,
        wall_liquid_U_W_m2K=0. if wall_only else .25,
        wall_vapor_U_W_m2K=0. if wall_only else .25, wall_axial_conductance_W_K=0.)
    tank = tank_module.LayeredTank(shape, parameters, properties)
    heights = np.linspace(0., shape.diameter, parameters.wall_node_count + 1)
    cumulative = np.array([shape.at_height(float(at)).wetted_inner_area_m2 for at in heights])
    fractions = tuple(float(value / shape.inner_surface_area_m2) for value in np.diff(cumulative))
    capacities = tuple(parameters.wall_heat_capacity_J_K * fraction for fraction in fractions)
    allocation = WallHeatAllocation(tuple(f"wall-{i + 1}" for i in range(3)), fractions,
        {} if wall_only else {"neck": (0., 0., 1.), "instrument": (.2, .5, .3)},
        "native public wetted-area geometry at three equally spaced height zones; declared penetration nodes")
    ins_params = vacuum.VacuumInsulationParameters(shape.inner_surface_area_m2,
        0. if wall_only else .0025, .08 if wall_only else .008,
        0. if wall_only else .002, 0. if wall_only else .025, .08,
        () if wall_only else (vacuum.LocalizedHeatPath("neck", .0014),
                              vacuum.LocalizedHeatPath("instrument", .0006)))
    boundary = Lh2dtVacuumInsulation(vacuum.VacuumInsulation(ins_params),
        evidence=evidence("native horizontal vessel .5 m diameter/.9 m straight shell/.1 m head depth; "
                          "effective warm-area equals native inner area by explicit synthetic assumption"))
    initial = tank.project_pressure(tank.initialize_saturated(200_000., .6,
                                    wall_temperature_K=60. if wall_only else 28.))
    reader = layered_inventory_reader(rigid_volume_m3=tank.total_rigid_volume_m3,
                                      wall_heat_capacities_j_k=capacities, basis=direct.basis)
    assert abs(reader(initial).total_energy_j - tank.total_energy_J(initial)) < 1e-8
    return tank, initial, boundary, allocation, reader


def wall_only_check(native_modules):
    tank, initial, boundary, allocation, reader = make_tank(native_modules, wall_only=True)
    seen = []
    start, duration, slope, initial_warm = 11., 2., .2, 280.
    callback = boundary.layered_wall_callback(allocation,
        warm_temperature_k=lambda at, _thermo: initial_warm + slope * (at - start),
        vacuum_pressure_pa_abs=0., clock_id="authored-absolute-insulation-clock", start_time_s=start,
        observer=lambda at, result: seen.append((at, result)))
    started = time.perf_counter()
    run = tank.simulate(initial, duration, .2, 280., wall_heat_callback=callback)
    elapsed = time.perf_counter() - started
    tau = 500. / .08
    expected = initial_warm + slope * (duration - tau) + (60. - initial_warm + slope * tau) * math.exp(-duration / tau)
    error = max(abs(value - expected) for value in run[-1].state.wall_temperatures_K)
    assert error < 1e-9 and min(at for at, _ in seen) == start and max(at for at, _ in seen) == start + duration
    first, last = reader(initial), reader(run[-1].state)
    assert abs(last.fluid_internal_energy_j - first.fluid_internal_energy_j) < 1e-8
    balance = InventoryBalance(first, last, 0., run[-1].cumulative_boundary_energy_J,
                                0., run[-1].cumulative_boundary_energy_J)
    assert not balance.violations(InventoryTolerances(1e-10, 1e-7, 1e-9))
    return expected, error, balance.energy_residual_j, len(run), len(seen), elapsed


def coupled_case(native_modules, step, *, reversed_heat=False):
    tank, initial, boundary, allocation, reader = make_tank(native_modules)
    start, duration = 7., .4
    calls = []

    def warm(at, _thermo):
        return (10. if reversed_heat else 295.) + .4 * (at - start)

    def pressure(at, thermo):
        # Authored state-dependent vacuum law; it is not a vacuum-pump model.
        return .002 * (1. + .01 * (sum(thermo.wall_temperatures_K) / 3. - 28.)) + .0001 * (at - start)

    callback = boundary.layered_wall_callback(allocation, warm_temperature_k=warm,
        vacuum_pressure_pa_abs=pressure, clock_id="authored-absolute-insulation-clock",
        start_time_s=start, observer=lambda at, result: calls.append((at, result)))
    started = time.perf_counter()
    run = tank.simulate(initial, duration, step, 295., wall_heat_callback=callback)
    elapsed = time.perf_counter() - started
    initial_inventory = reader(initial)
    balances, inventory_native_errors = [], []
    for row in run:
        current = reader(row.state)
        balance = InventoryBalance(initial_inventory, current, row.cumulative_boundary_mass_kg,
            row.cumulative_boundary_energy_J, 0., row.cumulative_boundary_energy_J)
        assert not balance.violations(InventoryTolerances(1e-10, 1e-7, 1e-9))
        balances.append(balance)
        inventory_native_errors.append(abs(current.total_energy_j - tank.total_energy_J(row.state)))
    times = [0.] + [row.time_s for row in run]
    states = [initial] + [row.state for row in run]
    accepted_heat, accepted_pressure = [], []
    for at, state in zip(times, states, strict=True):
        thermo = tank.thermo(state)
        q = boundary.partition(warm(start + at, thermo), state.wall_temperatures_K,
            pressure(start + at, thermo), allocation=allocation)
        accepted_heat.append(q.power.heat_w)
        accepted_pressure.append(q.vacuum_pressure_pa_abs)
    sampled_heat = sum((right - left) * (qr + ql) / 2. for left, right, ql, qr in
                       zip(times[:-1], times[1:], accepted_heat[:-1], accepted_heat[1:], strict=True))
    heat_integral = run[-1].cumulative_boundary_energy_J
    signed = -1. if reversed_heat else 1.
    assert signed * heat_integral > 0. and all(signed * q > 0. for q in accepted_heat)
    assert len({value for value in accepted_pressure}) == len(accepted_pressure)
    assert min(at for at, _ in calls) == start and max(at for at, _ in calls) == start + duration
    final = reader(run[-1].state)
    assert final.fluid_internal_energy_j > initial_inventory.fluid_internal_energy_j
    wrong_reader = layered_inventory_reader(rigid_volume_m3=tank.total_rigid_volume_m3,
        wall_heat_capacities_j_k=tuple(2. * tank.parameters.wall_heat_capacity_J_K * fraction
                                     for fraction in allocation.area_fractions), basis=initial_inventory.basis)
    wrong = wrong_reader(run[-1].state).total_energy_j - wrong_reader(initial).total_energy_j - heat_integral
    assert abs(wrong) > 1e-4
    row = {"dt": step, "steps": len(run), "heat_j": heat_integral,
        "fluid_delta_j": final.fluid_internal_energy_j - initial_inventory.fluid_internal_energy_j,
        "solid_delta_j": final.solid_internal_energy_j - initial_inventory.solid_internal_energy_j,
        "mass_residual_kg": max(abs(b.mass_residual_kg) for b in balances),
        "energy_residual_j": max(abs(b.energy_residual_j) for b in balances),
        "native_inventory_difference_j": max(inventory_native_errors),
        "sampled_heat_error_j": abs(sampled_heat - heat_integral), "wrong_wall_residual_j": wrong,
        "pressure_pa": run[-1].state.pressure_Pa, "wall_k": run[-1].state.wall_temperatures_K,
        "vacuum_start_pa": accepted_pressure[0], "vacuum_end_pa": accepted_pressure[-1],
        "callback_calls": len(calls), "elapsed_s": elapsed}
    print("coupled" + ("-reversed" if reversed_heat else ""), row, flush=True)
    return row, boundary, allocation, tank


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path, default=ROOT / "artifacts/native_packages")
    args = parser.parse_args()
    target = args.native_packages.resolve()
    if native_sha(target) != NATIVE_SHA:
        raise SystemExit("Install the exact optional LH2DT revision recorded in HANDOFF.md")
    host_sha = {name: file_sha(ROOT / name) for name in HOST_FILES}
    sys.path.insert(0, str(target))
    vacuum = importlib.import_module("lh2dt.vacuum_insulation")
    pipe_module = importlib.import_module("lh2dt.vacuum_jacketed_pipe")
    native_modules = (vacuum, importlib.import_module("lh2dt.layered_tank"),
        importlib.import_module("lh2dt.geometry"), importlib.import_module("lh2dt.properties"))
    incomplete = Lh2dtLowLevelProperties(CoolPropProperties("ParaHydrogen"),
        state_factory=native_modules[-1].ThermoState)
    try:
        getattr(incomplete, "specific_volume_derivatives_ph")
    except AttributeError as error:
        facade_failure = str(error)
    else:
        raise AssertionError("Re-review the expanded facade and its derivative qualification")
    started = time.perf_counter()
    static = static_checks(vacuum, pipe_module)
    static_elapsed = time.perf_counter() - started
    wall = wall_only_check(native_modules)
    rows = []
    for step in (.2, .1, .05):
        row, boundary, allocation, tank = coupled_case(native_modules, step)
        rows.append(row)
    reversed_row, _, _, _ = coupled_case(native_modules, .05, reversed_heat=True)
    wall_difference = max(abs(a - b) for a, b in zip(rows[-2]["wall_k"], rows[-1]["wall_k"], strict=True))
    pressure_difference = abs(rows[-2]["pressure_pa"] - rows[-1]["pressure_pa"])
    assert wall_difference < 1e-7 and pressure_difference < .01
    assert rows[-1]["sampled_heat_error_j"] < 1e-6
    params, base, gas_rows, uniform, heterogeneous, rad_error, part_error, ratio, failures, envelope, pipe_heat = static
    lines = ["# Native vacuum-insulation verification", "",
        f"Completed UTC: {datetime.now(UTC).isoformat()}.", "",
        f"Native MIT `lh2dt_models` revision `{REVISION}` (0.1.2); aggregate native module "
        f"SHA-256 `{NATIVE_SHA}`. The existing separately installed engine owns heat laws, "
        "geometry, EOS closure and tank RK4. No native source file or coefficient was modified.", "",
        "This is synthetic numerical verification. Parameters are authored geometry/construction "
        "inputs, with helium as the declared residual-gas identity. The effective gas coefficient "
        "and 0.08 Pa molecular-flow limit are synthetic test assumptions, not qualified material "
        "or vacuum-regime measurements. No heat-leak data or vendor performance was fitted.", "",
        "Primary references consulted: [2022 CODATA/NIST Stefan-Boltzmann constant]"
        "(https://physics.nist.gov/cgi-bin/cuu/Value?sigma), "
        "[NASA cryogenic insulation testing](https://ntrs.nasa.gov/citations/19990053342), "
        "[NASA MLI repeatability study](https://ntrs.nasa.gov/citations/20180000366), and "
        "[NASA continuum/kinetic MLI venting model](https://ntrs.nasa.gov/citations/20180002393). "
        "These support independent thermal limits and the need for pressure/construction-specific "
        "qualification; no source table, plot or measured coefficient is reproduced. "
        "Public metadata were inspected without acquiring a dataset or claiming raw-data rights.", "",
        f"Static native parameters: `{params}`.", "",
        f"At 295/24 K and 0.006 Pa absolute, native parallel-path heat is {base.power.heat_w:.12g} W: "
        f"`{dict(base.path_heat_w)}`. Radiation/NIST verification error {rad_error:.3g} W; "
        "zero gradient returns exactly 0 W for every path, and swapping boundary temperatures "
        "reverses the complete signed heat within 1e-12 W. The native reported effective UA "
        "is 0 at exactly zero gradient; it is a diagnostic ratio, not the differential conductance.", "",
        f"Doubling both absolute temperatures in the radiation-only case gives heat ratio {ratio:.12g}. "
        f"Equal-temperature area partition total {uniform.power.heat_w:.12g} W agrees with the "
        "unpartitioned native boundary within 1e-12 W. Three heterogeneous wall zones preserve "
        f"area and separate penetration allocations; zone heat `{heterogeneous.zone_heat_w}` W "
        f"matches the independent reference to {part_error:.3g} W. "
        "Independent reference equations are used only in this verification script, not as another solver.", "",
        "| Absolute annulus pressure (Pa) | Native gas-only heat (W) |", "|---:|---:|"]
    lines += [f"| {pressure:.12g} | {heat:.12g} |" for pressure, heat in gas_rows]
    lines += ["", f"Native pipe-envelope geometry: length 1.3 m; bore/process-outer/jacket-inner "
        f"diameters .018/.022/.060 m; fluid volume {envelope.fluid_volume_m3:.12g} m3; "
        f"process wall volume {envelope.process_wall_volume_m3:.12g} m3; "
        f"jacket-reference area {envelope.jacket_inner_surface_area_m2:.12g} m2; radial gap "
        f"{envelope.radial_vacuum_gap_m:.12g} m. Native `make_insulation` retains this jacket area, "
        f"giving {pipe_heat.power.heat_w:.12g} W at 295/24 K and .006 Pa. "
        "This checks the actual pipe-envelope heat law; the stock DynamicHEMPipe has no callable "
        "external heat hook, so it is not silently replaced by a state-varying UA.", "",
        "## Actual native layered tank boundary", "",
        "The tank is a .5 m diameter, .9 m straight cylinder with two .1 m deep ellipsoidal heads; "
        "one liquid cell, one vapor cell and three wall nodes. Its native inner area is explicitly "
        "used as an effective warm reference area. Source pressure is 200 kPa absolute, liquid "
        "fill fraction .6, and native para-H2 HEOS properties preserve their energy reference. "
        "The wall capacity is 500 J/K, partitioned using public geometric wetted-area differences. "
        f"Area fractions: `{allocation.area_fractions}`; native tank area {tank.shape.inner_surface_area_m2:.12g} m2. "
        "Neck allocation is (0,0,1), instrument allocation (.2,.5,.3). "
        "Built-in ambient UA and axial wall conduction are explicitly zero to avoid double-counting. "
        "The coupled cases use .25 W/(m2 K) wall/fluid coefficients; all remaining default native "
        "phase-interface and EOS responsibilities remain native.", "",
        "The analytic wall-only case removes wall/fluid exchange and radiation/gas/local paths, "
        "uses 0.08 W/K distributed solid conductance, and applies a linearly warming reservoir "
        "on absolute time 11-13 s. Native callbacks receive actual wall states and the declared "
        f"operation clock. Expected final wall T {wall[0]:.12g} K; maximum error {wall[1]:.3g} K; "
        f"independent energy residual {wall[2]:.3g} J; {wall[3]} accepted steps / {wall[4]} "
        "callback evaluations. Fluid internal energy is unchanged within 1e-8 J.", "",
        "Coupled 0.4 s cases use absolute time 7-7.4 s, initial wall 28 K, "
        "effective emissivity .0025, MLI/support conductances .008/.002 W/K, "
        "residual coefficient .025 W/(m2 K Pa), and neck/instrument .0014/.0006 W/K. "
        "Warm T is 295+.4*(t-7) K, while synthetic absolute vacuum pressure is "
        ".002*(1+.01*(mean wall T-28))+.0001*(t-7) Pa. Reversed heat uses a 10 K warm-side "
        "intercept with the same explicit laws. This state law tests a callback; it is not a "
        "vacuum-pump or gas-adsorption model.", "",
        "| Case / dt (s) | Steps | Native external heat (J) | Fluid/solid energy change (J) | "
        "Max independent mass residual (kg) | Max independent energy residual (J) | "
        "Accepted-sample trapezoid error (J) | Runtime (s) |",
        "|---|---:|---:|---|---:|---:|---:|---:|"]
    for label, row in [("heating", row) for row in rows] + [("reversed", reversed_row)]:
        lines.append(f"| {label} / {row['dt']} | {row['steps']} | {row['heat_j']:.12g} | "
            f"{row['fluid_delta_j']:.12g} / {row['solid_delta_j']:.12g} | "
            f"{row['mass_residual_kg']:.3g} | {row['energy_residual_j']:.3g} | "
            f"{row['sampled_heat_error_j']:.3g} | {row['elapsed_s']:.6g} |")
    lines += ["", "The independent reader uses sum(m*h)-p*rigid_volume plus explicitly supplied "
        "wall capacities and returns existing ConservedInventory objects. Existing InventoryBalance "
        "checks use 1e-10 kg, 1e-7 J and 1e-9 relative budgets. Independent inventory/native total "
        f"energy agreement is at most {max(r['native_inventory_difference_j'] for r in rows + [reversed_row]):.3g} J. "
        "Boundary sampled quadrature is independent of native RK-stage cumulative heat; "
        f"finest error {rows[-1]['sampled_heat_error_j']:.3g} J passes a 1e-6 J gate. "
        f"Last two heating refinements differ by {wall_difference:.3g} K maximum wall temperature "
        f"and {pressure_difference:.3g} Pa tank pressure, against 1e-7 K / .01 Pa gates. "
        "These numerical gates are fixed before reporting the result.", "",
        f"Finest heating vacuum {rows[-1]['vacuum_start_pa']:.12g} -> {rows[-1]['vacuum_end_pa']:.12g} Pa, "
        f"pressure {rows[-1]['pressure_pa']:.12g} Pa, wall T `{rows[-1]['wall_k']}` K. "
        f"Reversed external heat {reversed_row['heat_j']:.12g} J is retained; fluid can still "
        "gain energy from a warmer wall while the complete closed inventory loses energy. "
        f"Deliberately doubling wall capacity in the independent reader gives residual "
        f"{rows[-1]['wrong_wall_residual_j']:.12g} J (reversed {reversed_row['wrong_wall_residual_j']:.12g} J); "
        "both fail the 1e-4 J negative-check threshold.", "",
        "## Preserved limitations and local receiving requests", ""]
    lines += [f"- {label}: rejected with `{message}`." for label, message in failures]
    lines.append(f"- The existing low-level property facade is unavailable for this layered-tank "
        f"API: `{facade_failure}`. Its earlier actual initialization attempt failed at "
        "LayeredTank.project_pressure. The successful cases explicitly select original native "
        "HydrogenProperties with HEOS ParaHydrogen; saturated-liquid enthalpy matches the host "
        "reference at 200 kPa within 1e-8 J/kg. No unsupported derivative is invented and "
        "no automatic property fallback is added.")
    lines += ["- Native zero-area wall fractions pass the partition's nonnegative-fraction check "
        "but fail its positive-area zone construction. Add a public zero-zone treatment that "
        "preserves discrete penetration placement, with limits and tests; do not renormalize it silently.",
        "- Add public callable signed external-heat inputs to DynamicHEMPipe and other lumped "
        "equipment. Preserve native wall/fluid equations, RK-stage heat ledgers, units and absolute clocks; "
        "a mutable or fitted UA is not the general nonlinear boundary.",
        "- Expose public wall zone areas/capacities and decomposed per-zone path results. "
        "The present tank composition derives geometry through public methods and independently "
        "declares capacity; the native layered partition currently returns totals only.",
        "- The native molecular gas law stops at the declared pressure limit. Continuum/transition "
        "transport, changing residual gas, MLI compression/aging, warm-jacket thermal storage, "
        "loss-of-vacuum ingress/condensation and measured calorimeter qualification remain open. "
        "No native default is promoted to a construction-specific material coefficient.", "",
        f"Static checks runtime {static_elapsed:.6g} s; analytic wall case {wall[-1]:.6g} s. "
        "Runtimes describe this local workload only.", "", "Source/test/script SHA-256:", ""]
    lines += [f"- `{name}`: `{digest}`." for name, digest in host_sha.items()]
    for name in ("vacuum_insulation.py", "vacuum_jacketed_pipe.py", "layered_tank.py"):
        lines.append(f"- Native `lh2dt/{name}`: `{file_sha(target / 'lh2dt' / name)}`.")
    lines += ["", "No external repository edits, messages, data downloads, new dependency installation "
        "or measured/vendor validation occurred. This first executable insulation level remains "
        "a qualified software composition with authored verification parameters."]
    if native_sha(target) != NATIVE_SHA or any(file_sha(ROOT / name) != digest for name, digest in host_sha.items()):
        raise RuntimeError("Source changed during computation; report withheld")
    (ROOT / "research/native_insulation.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote research/native_insulation.md", flush=True)


if __name__ == "__main__":
    main()
