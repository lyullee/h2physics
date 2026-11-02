"""Actual pinned cold-side recovery, native conservation and analytic limits."""

import hashlib
import importlib
import importlib.metadata
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_dynamics import Lh2dtDynamicEquipment
from h2physics.adapters.lh2dt_equipment import Lh2dtEquipmentNetwork, Lh2dtSharedValve
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_reliquefier import (
    ColdSideBoundary,
    Lh2dtDynamicReliquefier,
    Lh2dtSteadyReliquefier,
    ReliquefactionDomain,
    ReliquefierClosureError,
    liquid_mass_fraction,
)
from h2physics.core import Origin
from h2physics.equipment import BoundaryPower
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "artifacts/native_packages"
NATIVE_SHA = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = ("src/h2physics/adapters/lh2dt_reliquefier.py", "tests/test_lh2dt_reliquefier.py",
    "scripts/check_reliquefier_integration.py", "src/h2physics/adapters/lh2dt_dynamics.py",
    "src/h2physics/adapters/lh2dt_equipment.py", "src/h2physics/adapters/lh2dt_properties.py",
    "src/h2physics/dynamics.py", "src/h2physics/thermo/coolprop.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sha():
    digest = hashlib.sha256()
    for path in sorted((TARGET / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def properties(native, fluid="ParaHydrogen"):
    direct = CoolPropProperties(fluid, quality_roundoff_tolerance=1e-8)
    facade = Lh2dtLowLevelProperties(direct, state_factory=native.ThermoState)
    bridge = Lh2dtProperties(facade, reference_id=direct.basis.reference_id)
    return direct, facade, bridge


def domain():
    return ReliquefactionDomain(1e4, 10e6, 14.1, 1000,
                                "authored-synthetic-domain-not-equipment-qualification")


def make_dynamic(native, *, fluid_ua=20., cold_ua=20., cap=5., cold=18., wall_capacity=2.):
    direct, facade, bridge = properties(native)
    boundary = ColdSideBoundary("absolute-cold-clock", 10., 30., cold,
                                "authored-cold-reservoir", Origin.SYNTHETIC)
    component = native.DynamicReliquefier(.001, wall_capacity, fluid_ua, 18., cold_ua, cap, facade)
    adapter = Lh2dtDynamicReliquefier(component, bridge, state_factory=native.ThermoState,
                                      domain=domain(), cold_boundary=boundary)
    return direct, adapter


def make_run(native, model, initial, *, duration, step, start=10., flowing=False):
    binding = model.inventory_binding("cold-volume", initial, node_factory=native.dynamic_vaporizer_node)
    graph = Lh2dtEquipmentNetwork(native.SteadyNetwork(model.bridge.native), model.bridge,
                                  state_factory=native.ThermoState)
    graph.add_boundary("cold-volume", model.fluid(initial))
    if flowing:
        direct = model.bridge.native.provider
        graph.add_boundary("feed", direct.state_pt(2.2e5, 35))
        graph.add_boundary("delivery", direct.state_pt(1.8e5, 25))
        for identity, left, right in (("feed-valve", "feed", "cold-volume"),
                                     ("outlet-valve", "cold-volume", "delivery")):
            component = Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), model.bridge,
                NozzleOpening.circular(identity, .0001, effective_area_factor=1,
                                        area_basis_id="authored-effective-area"),
                result_factory=native.ValveResult, opening_fraction=1., allow_reverse=False)
            graph.add_link(identity, left, right, component, power_reader=lambda _: BoundaryPower(),
                source_port_id=f"{identity}/in", target_port_id=f"{identity}/out")
    run = Lh2dtDynamicEquipment(graph, {"cold-volume": binding.inventory_node},
        simulator_factory=native.DynamicNetworkSimulator).run(duration, step,
            start_time_s=start, clock_id=model.cold_boundary.clock_id)
    return binding, run


def steady_checks(native, lines):
    lines += ["## Steady saturated latent-heat and capacity limits", "",
        "The actual native Reliquefier receives an explicit saturation-pressure/quality "
        "target. For a saturated-vapor inlet at fixed pressure, the independent latent-heat "
        "oracle is newly condensed fraction = removed_heat/(mdot*(h_g-h_l)). Saturated "
        "enthalpies come from the selected HEOS provider, so this is a conservation oracle "
        "rather than independent property validation. No outlet quality is overwritten.", "",
        "| Fluid | Pressure Pa | Capacity / latent duty | Outlet liquid fraction | "
        "Oracle absolute error | Heat into fluid W | Energy residual W |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for fluid in ("Hydrogen", "ParaHydrogen", "OrthoHydrogen"):
        direct, facade, bridge = properties(native, fluid)
        for pressure in (1e5, 3e5):
            liquid, vapor = direct.saturated(pressure, 0), direct.saturated(pressure, 1)
            latent_duty = .001*(vapor.enthalpy_j_kg-liquid.enthalpy_j_kg)
            for fraction in (.1, .5, 1., 2.):
                model = Lh2dtSteadyReliquefier(native.Reliquefier(fraction*latent_duty, facade),
                    bridge, state_factory=native.ThermoState, domain=domain(), component_id="steady-recovery")
                result = model.evaluate(vapor, outlet_pressure_pa=pressure, mass_flow_kg_s=.001)
                error = abs(result.outlet_liquid_mass_fraction-min(fraction, 1))
                if error > 2e-8 or abs(result.energy_residual_w) > 1e-6:
                    raise AssertionError("Native latent-heat recovery gate failed")
                lines.append(f"| {fluid} | {pressure:g} | {fraction:g} | "
                    f"{result.outlet_liquid_mass_fraction:.12g} | {error:.8g} | "
                    f"{result.power.heat_w:.10g} | {result.energy_residual_w:.8g} |")
    direct, facade, bridge = properties(native)
    limited = Lh2dtSteadyReliquefier(native.Reliquefier(1., facade), bridge,
        state_factory=native.ThermoState, domain=domain(), component_id="limited-warm-gas")
    gas = limited.evaluate(direct.state_pt(2e5, 80), outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    complete = Lh2dtSteadyReliquefier(native.Reliquefier(1e5, facade), bridge,
        state_factory=native.ThermoState, domain=domain(), component_id="mixed-feed")
    mixed = complete.evaluate(direct.saturated(2e5, .3), outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    if gas.outlet_liquid_mass_fraction != 0 or abs(mixed.net_liquid_production_kg_s-.0003) > 1e-10:
        raise AssertionError("Native gas/counted-preexisting-liquid gate failed")
    lines += ["", f"A 1 W capacity at 0.001 kg/s, 80 K / 200 kPa leaves gas at "
        f"{gas.outlet.temperature_k:.12g} K with zero liquid production. Capacity limitation "
        "does not force saturation. A separate inlet with 70% existing liquid gives "
        f"{mixed.liquid_outflow_kg_s:.12g} kg/s total liquid but only "
        f"{mixed.net_liquid_production_kg_s:.12g} kg/s newly produced liquid.", "",
        f"The explicitly selected inherited endpoint-quality roundoff policy is 1e-8; "
        f"this final pair's facade recorded {facade.quality_adjustment_count} adjustments, "
        f"maximum {facade.maximum_quality_adjustment:.12g}. These diagnostics do not "
        "authorize a physical phase or spin conversion."]
    print("24 native steady latent/capacity points plus superheated/preexisting-liquid checks passed", flush=True)


def finite_checks(native, lines):
    lines += ["", "## Native finite fluid/wall cooling and condensation", "",
        "A 0.001 m3 rigid mixed volume starts at saturated vapor at 200 kPa. Wall C=2 J/K, "
        "initial wall/cold reservoir 18 K, fluid-wall UA=20 W/K, reservoir-wall UA=20 W/K "
        "and native maximum_cooling=5 W. The 5 W cap limits fluid-wall exchange; it "
        "does not cap the cold-reservoir heat into the wall. Native EOS/inventory "
        "feedback determines pressure and actual condensation. No pressure or quality "
        "is imposed after initialization. All parameters are synthetic.", "",
        "| Step s | Final pressure Pa | Final liquid hold-up kg | Cold-side heat integral J | "
        "Max mass residual kg | Max energy residual J | Analytic fluid-U error J | "
        "Analytic wall-T error K |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    runs = []
    for step in (.08, .04, .02):
        direct, model = make_dynamic(native)
        initial = model.initialize(direct.saturated(2e5, 1), wall_temperature_k=18)
        _, run = make_run(native, model, initial, duration=2., step=step)
        last = run.steps[-1]
        fluid = last.equipment.node_states["cold-volume"]
        fraction = liquid_mass_fraction(fluid)
        mass_error = max(abs(row.balances["cold-volume"].mass_residual_kg) for row in run.steps)
        energy_error = max(abs(row.balances["cold-volume"].energy_residual_j) for row in run.steps)
        final_native = last.native.states["cold-volume"]
        u_error = abs(final_native.internal_energy_J-initial.internal_energy_J+5*2)
        wall_error = abs(final_native.wall_temperature_K-(18+5/20*(1-math.exp(-20/2*2))))
        if not 0 < fraction < 1 or mass_error > 1e-12 or energy_error > 1e-8:
            raise AssertionError("Finite native condensation/inventory gate failed")
        if u_error > 1e-8 or wall_error > 1e-7:
            raise AssertionError("Independent capped-fluid/exponential-wall cooling gate failed")
        liquid_mass = last.inventories["cold-volume"].mass_kg*fraction
        lines.append(f"| {step:g} | {fluid.pressure_pa:.12g} | {liquid_mass:.12g} | "
            f"{last.balances['cold-volume'].external_heat_j:.12g} | {mass_error:.8g} | {energy_error:.8g} | "
            f"{u_error:.8g} | {wall_error:.8g} |")
        runs.append(run)
    coarse_p = runs[-2].steps[-1].equipment.node_states["cold-volume"].pressure_pa
    fine_p = runs[-1].steps[-1].equipment.node_states["cold-volume"].pressure_pa
    difference = abs(coarse_p/fine_p-1)
    if difference > 1e-6:
        raise AssertionError("Native condensation pressure refinement gate failed")
    lines += ["", f"Finest-two-run pressure relative difference: {difference:.12g}, gate 1e-6. "
        "Liquid hold-up is stored material, not a collected product or a phase-separated outlet. "
        "The fluid-wall cap is active throughout this case, giving independent U(t)=U0-5*t "
        "and Twall(t)=18+(5/20)*(1-exp(-20*t/2)) references. No convergence order is "
        "inferred from a pressure difference at the floating-point floor."]
    print("native sealed fluid+wall condensation and refinement passed", flush=True)


def analytic_and_modes(native, lines):
    direct, model = make_dynamic(native, fluid_ua=0, cold_ua=1,
                                cold=lambda t: 18+.1*(t-10))
    initial = model.initialize(direct.state_pt(2e5, 35), wall_temperature_k=30)
    _, run = make_run(native, model, initial, duration=1., step=.05)
    final = run.steps[-1].native.states["cold-volume"]
    expected = 18+.1*(1-2)+(30-18+.1*2)*math.exp(-.5)
    error = abs(final.wall_temperature_K-expected)
    if error > 1e-7 or final.internal_energy_J != initial.internal_energy_J or final.mass_kg != initial.mass_kg:
        raise AssertionError("Independent cold-side wall-relaxation/clock gate failed")
    direct, off = make_dynamic(native, cold_ua=0)
    initial_off = off.initialize(direct.state_pt(2e5, 35), wall_temperature_k=25)
    _, off_run = make_run(native, off, initial_off, duration=.2, step=.02)
    off_balance = off_run.steps[-1].balances["cold-volume"]
    if off_balance.external_heat_j != 0 or abs(off_balance.energy_residual_j) > 1e-8:
        raise AssertionError("Native external-cooling-off conservation gate failed")
    direct, cap = make_dynamic(native)
    initial_cap = cap.initialize(direct.state_pt(2e5, 35), wall_temperature_k=25)
    rates = cap.derivative(initial_cap, cap.fluid(initial_cap), 0, 0, time_s=10)
    if rates.fluid_wall_heat_w != -5 or rates.external_power.heat_w != -140:
        raise AssertionError("Native external cold-side versus fluid-wall cap distinction failed")
    direct, zero = make_dynamic(native)
    zero_state = zero.initialize(direct.state_pt(2e5, 18), wall_temperature_k=18)
    zero_step = zero.step(zero_state, zero.fluid(zero_state), 0, 0, time_s=10, time_step_s=.1)
    zero_error = abs(zero_step.native.state.wall_temperature_K-18)
    if zero_error > 1e-12 or abs(zero_step.final_rates.external_power.heat_w) > 1e-12:
        raise AssertionError("Native zero thermal gradient gate failed")
    lines += ["", "## Independent cooling/clock and inactive limits", "",
        "With zero fluid-wall UA, wall C=2 J/K and reservoir-wall UA=1 W/K, the cold "
        "temperature is 18+0.1*(absolute_time-10) K on the declared 10–30 s support. "
        "The native run advances 10–11 s with the existing absolute-clock driver. "
        "The original analytic forced-exponential wall reference is independent of "
        "the native integrator; fluid mass/U remain exactly unchanged.", "",
        f"Analytic final wall T={expected:.12g} K; absolute error={error:.12g} K, gate 1e-7 K. "
        f"A separate equal-temperature native step has wall deviation {zero_error:.12g} K "
        "against a 1e-12 K/W roundoff budget; native returned values are unchanged.", "",
        "With external cold-side UA=0, the sealed system still exchanges fluid/wall "
        "heat and stores finite gas. Total fluid+wall energy remains constant; the "
        "native constructor allows this mode without making the cooling cap zero. "
        "Hydraulic isolation (zero flows) independently leaves cold-side cooling active.", "",
        "At 35 K fluid, 25 K wall, 18 K reservoir and both UAs 20 W/K, the actual "
        "native derivative gives -5 W into fluid from wall but -140 W from reservoir "
        "into the combined fluid/wall system. Calling the former a system-wide "
        "refrigerator capacity would be incorrect. No COP/electrical input or cycle "
        "efficiency is inferred."]
    print("analytic cold-reservoir clock, zero-gradient and cooling-off limits passed", flush=True)


def flowing_check(native, lines):
    direct, model = make_dynamic(native)
    initial = model.initialize(direct.saturated(2e5, 1), wall_temperature_k=18)
    _, run = make_run(native, model, initial, duration=.1, step=.02, flowing=True)
    last = run.steps[-1]
    balance = last.balances["cold-volume"]
    fluid = last.equipment.node_states["cold-volume"]
    if abs(balance.mass_residual_kg) > 1e-12 or abs(balance.energy_residual_j) > 1e-8:
        raise AssertionError("Open native recovery inventory gate failed")
    lines += ["", "## Flowing finite native recovery", "",
        "The same finite condenser connects a 220 kPa/35 K H2 feed and a 180 kPa "
        "delivery boundary through two explicit 0.1 mm shared-nozzle valves with "
        "effective-area factor 1 and reverse flow disabled. The existing common "
        "nozzle owns each hydraulic closure; the native dynamic integrator owns "
        "every fluid/wall state update. The run is 10–10.1 s at 0.02 s steps.", "",
        f"Final pressure={fluid.pressure_pa:.12g} Pa; stored liquid fraction="
        f"{liquid_mass_fraction(fluid):.12g}; mass residual={balance.mass_residual_kg:.12g} kg; "
        f"energy residual={balance.energy_residual_j:.12g} J; external reservoir heat="
        f"{balance.external_heat_j:.12g} J; net transported enthalpy="
        f"{balance.transported_enthalpy_j:.12g} J. The native outlet is well mixed; "
        "no phase separator, collected liquid tank or return efficiency is invented."]
    print("actual native flowing condenser plus shared-nozzle boundaries passed", flush=True)


def failures(native, lines):
    direct, facade, bridge = properties(native)
    steady = native.Reliquefier(100., facade)
    direct2, model = make_dynamic(native)
    initial = model.initialize(direct2.state_pt(2e5, 35), wall_temperature_k=25)
    tests = (
        ("native steady zero flow unsupported", lambda: steady.evaluate(facade.from_pT(2e5, 35), 2e5, 0)),
        ("native steady zero capacity constructor unsupported", lambda: native.Reliquefier(0, facade)),
        ("native saturation target above critical", lambda: steady.evaluate(facade.from_pT(2e5, 35), 2e6, .001)),
        ("native finite over-withdrawal", lambda: model.native.step(initial,
             model.bridge.native.from_pT(2e5, 35), 0, 1, 1)),
        ("native semantic node lacks cold-time callback keyword",
         lambda: native.dynamic_reliquefier_node("r", model.native, initial,
                                                  ambient_temperature_K=lambda t: 18)),
        ("host clock support breach", lambda: model.derivative(initial, model.fluid(initial), 0, 0, time_s=31)),
    )
    lines += ["", "## Retained native failures and capability limits", "",
              "| Attempt | Actual rejected result |", "|---|---|"]
    for label, callback in tests:
        try:
            callback()
        except (ValueError, TypeError) as error:
            message = " ".join(str(error).split()).replace("|", "/")
            lines.append(f"| {label} | {message} |")
        else:
            raise AssertionError(f"Expected native/capability failure did not occur: {label}")
    lines += ["", "The checked finite condenser only needs the shared native facade's "
        "rho/U, PH/PT and saturation capabilities. Its absent layered pressure-projection "
        "derivatives are not called or silently replaced. Time-varying cold forcing "
        "explicitly selects native dynamic_vaporizer_node over the actual inherited "
        "DynamicReliquefier component; no heat equation or RK step is copied."]
    direct3, rejected = make_dynamic(native)
    state = rejected.initialize(direct3.state_pt(2e5, 35), wall_temperature_k=25)
    rejected.domain = replace(rejected.domain, minimum_temperature_k=34.999)
    try:
        rejected.step(state, rejected.fluid(state), 0, 0, time_s=10, time_step_s=.01)
    except ReliquefierClosureError as error:
        lines += ["", "A completed actual native step is retained when the declared "
            f"minimum fluid temperature 34.999 K is crossed: raw returned fluid T="
            f"{error.native.fluid.temperature_K:.12g} K, raw fluid mass="
            f"{error.native.state.mass_kg:.12g} kg. The full native state/derivative/"
            "step result remains in the exception; it is not rewritten or accepted."]
    else:
        raise AssertionError("Completed out-of-domain native finite step was accepted")


def main():
    start = time.perf_counter()
    host_sha = {name: sha(ROOT / name) for name in HOST_FILES}
    if native_sha() != NATIVE_SHA:
        raise RuntimeError("Review/install the pinned native LH2DT source snapshot")
    sys.path.insert(0, str(TARGET))
    native = importlib.import_module("lh2dt")
    if Path(native.__file__).resolve() != (TARGET / "lh2dt/__init__.py").resolve():
        raise RuntimeError("Imported native package differs from the selected target")
    lines = ["# Native steady and finite-volume reliquefaction verification", "",
        "Synthetic numerical/interface/conservation evidence only. No measured "
        "boiloff-recovery efficiency, refrigeration cycle or manufacturer map is qualified.", "",
        f"LH2DT {importlib.metadata.version('lh2dt_models')}, revision "
        "b2f276333c1b1793c39f25763703d196d36742ec; "
        f"CoolProp {importlib.metadata.version('CoolProp')}.", "",
        "| Native source | SHA-256 |", "|---|---|",
        f"| Native top-level ordered filename+bytes | {NATIVE_SHA} |"]
    lines += [f"| lh2dt/{name} | {sha(TARGET/'lh2dt'/name)} |" for name in (
        "reliquefier.py", "dynamic_reliquefier.py", "dynamic_vaporizer.py", "dynamic_network.py")]
    lines += [f"| Installed MIT license | "
        f"{sha(TARGET/'lh2dt_models-0.1.2.dist-info/licenses/LICENSE')} |", "",
        "Host source/test/script fingerprints, guarded at the beginning and end:", "",
        "| File | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | {digest} |" for name, digest in host_sha.items()]
    lines.append("")
    steady_checks(native, lines)
    finite_checks(native, lines)
    analytic_and_modes(native, lines)
    flowing_check(native, lines)
    failures(native, lines)
    lines += ["", "## Sources, rights and remaining scope", "",
        "Actual native states, derivatives, step results, dynamic nodes and accepted "
        "network/integrator rows remain available. External heat is signed into fluid "
        "plus wall; fluid-wall heat is internal and cancels from that combined ledger. "
        "A liquid mass fraction denotes actual equilibrium material, not collection "
        "efficiency. Native mass loss/depletion, below-triple states or unavailable "
        "quality do not receive a clipping, saturation or reverse-flow repair.", "",
        "Primary references: [native steady source]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/reliquefier.py), "
        "[native finite source]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_reliquefier.py), "
        "[CoolProp phase/quality API](https://coolprop.org/coolprop/HighLevelAPI.html), "
        "[hydrogen EOS](https://doi.org/10.1063/1.3160306), "
        "[first law](https://www.grc.nasa.gov/www/k-12/airplane/thermo1.html). "
        "Native code is separately installed under [MIT]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE); "
        "no code, worked examples, mechanism, measured data or equipment curves are bundled.", "",
        "Receiving/research gaps: public time-aware cold-side naming and independent "
        "reservoir-capacity versus internal-exchange-cap semantics, native averaged "
        "standalone-step boundary integrals, depletion/event localization, phase-selective "
        "withdrawal/collection and actual apparatus/cycle power data. No electrical "
        "power/COP is supplied by this cold-reservoir model.", "",
        f"Elapsed local replay time: {time.perf_counter()-start:.8g} s."]
    if native_sha() != NATIVE_SHA or any(sha(ROOT/name) != digest for name, digest in host_sha.items()):
        raise RuntimeError("Source bytes changed during replay; report not written")
    lines += ["", "Native and host source/test/script begin/end byte guards passed."]
    (ROOT / "research/native_reliquefaction.md").write_text("\n".join(lines)+"\n",
                                                         encoding="utf-8", newline="\n")
    print("wrote research/native_reliquefaction.md", flush=True)


if __name__ == "__main__":
    main()
