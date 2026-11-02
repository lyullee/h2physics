"""Replay a closed two-fluid native exchanger and independent thermal limits."""

import hashlib
import importlib
import importlib.metadata as metadata
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import brentq

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_heat_exchanger import (
    FiniteHeatExchangerSide,
    HeatExchangerCoupling,
    HeatExchangerDomain,
    Lh2dtFiniteHeatExchanger,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.core import Origin
from h2physics.thermo import CoolPropProperties

REVISION = "b2f276333c1b1793c39f25763703d196d36742ec"
NATIVE_SOURCE_SHA256 = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"


def native_hash(directory):
    digest = hashlib.sha256()
    for file in sorted(directory.glob("*.py")):
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def main():
    import CoolProp
    import CoolProp.CoolProp as cp

    root = Path(__file__).resolve().parents[1]
    target = root/"artifacts/native_packages"
    native_directory = target/"lh2dt"
    if not native_directory.is_dir() or native_hash(native_directory) != NATIVE_SOURCE_SHA256:
        raise SystemExit("Install the reviewed native LH2DT snapshot; current module bytes are unavailable/different")
    native_before = native_hash(native_directory)
    sources = ("src/h2physics/adapters/lh2dt_heat_exchanger.py", "tests/test_lh2dt_heat_exchanger.py",
        "scripts/check_heat_exchanger_integration.py", "src/h2physics/adapters/lh2dt_properties.py",
        "src/h2physics/adapters/lh2dt.py", "src/h2physics/thermo/coolprop.py", "src/h2physics/dynamics.py")
    before_hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}
    native_files = {name: hashlib.sha256((native_directory/name).read_bytes()).hexdigest()
                    for name in ("dynamic_vaporizer.py", "dynamic_network.py", "network.py", "properties.py")}
    sys.path.insert(0, str(target))
    dynamic = importlib.import_module("lh2dt.dynamic_network")
    vaporizer = importlib.import_module("lh2dt.dynamic_vaporizer")
    network = importlib.import_module("lh2dt.network")
    native_state_type = importlib.import_module("lh2dt.properties").ThermoState
    if Path(dynamic.__file__).resolve().parent != native_directory.resolve():
        raise SystemExit("Native import did not resolve to the reviewed snapshot")
    started = perf_counter()

    def make(*, g=2., fluid_wall=(5., 6.), capacities=(100., 150.), temperatures=(400., 250.),
             wall_temperatures=None):
        sides = []
        for i, (name, fluid, pressure, volume) in enumerate((
                ("left", "Hydrogen", 3e5, .01), ("right", "ParaHydrogen", 2e5, .02))):
            direct = CoolPropProperties(fluid)
            properties = Lh2dtLowLevelProperties(direct, state_factory=native_state_type)
            bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
            native = vaporizer.DynamicVaporizer(volume, capacities[i], fluid_wall[i], 300., g, 1e6, properties)
            initial = native.initialize(properties.from_pT(pressure, temperatures[i]),
                wall_temperature_K=None if wall_temperatures is None else wall_temperatures[i])
            sides.append(FiniteHeatExchangerSide(name, native, initial, bridge,
                HeatExchangerDomain(200., 650., 1e3, 1e7, 1e-8,
                    ("gas", "supercritical_gas", "supercritical")), "authored-finite-fluid-inventory"))
        return Lh2dtFiniteHeatExchanger(*sides,
            HeatExchangerCoupling(g, "authored-wall-to-wall-conductance", Origin.SYNTHETIC, f"LH2DT:{REVISION}"),
            native_side_node_factory=dynamic.dynamic_vaporizer_node,
            native_network_factory=network.SteadyNetwork,
            native_simulator_factory=dynamic.DynamicNetworkSimulator, equipment_id="authored-two-fluid-HX")

    def run(model, duration, step):
        return model.run(duration_s=duration, maximum_step_s=step, start_time_s=100.,
                         clock_id="authored-two-fluid-operation-clock")

    reference_model = make()
    coarse, medium, fine = [run(make(), 20., step) for step in (.5, .25, .125)]
    wall_limit = run(make(fluid_wall=(0., 0.)), 30., .25)
    zero = run(make(g=0.), 5., .25)
    reversed_heat = run(make(fluid_wall=(5., 5.), capacities=(10., 10.), temperatures=(250., 450.),
                             wall_temperatures=(400., 300.)), 20., .1)
    equilibrium_run = run(reference_model, 1000., .5)
    all_runs = (coarse, medium, fine, wall_limit, zero, reversed_heat, equilibrium_run)
    max_mass = max(abs(s.balance.mass_residual_kg) for r in all_runs for p in r.points for s in p.sides.values())
    max_side_energy = max(abs(s.balance.energy_residual_j) for r in all_runs for p in r.points for s in p.sides.values())
    max_global_energy = max(abs(p.global_energy_residual_j) for r in all_runs for p in r.points)
    max_coupling = max(abs(p.integrated_coupling_residual_j) for r in all_runs for p in r.points)
    max_opposite_rate = max(abs(sum(s.coupling_heat_into_side_w for s in p.sides.values()))
                            for r in all_runs for p in r.points)

    elapsed_wall = wall_limit.time_s-100.
    mean = (100.*400.+150.*250.)/250.
    difference = 150.*np.exp(-2.*(1./100.+1./150.)*elapsed_wall)
    analytic_wall_error = max(
        float(np.max(abs(np.array([p.sides["left"].native_state.wall_temperature_K for p in wall_limit.points])
                         -(mean+150./250.*difference)))),
        float(np.max(abs(np.array([p.sides["right"].native_state.wall_temperature_K for p in wall_limit.points])
                         -(mean-100./250.*difference)))))

    native_eos = [CoolProp.AbstractState("HEOS", fluid) for fluid in ("Hydrogen", "ParaHydrogen")]
    sides = (reference_model.left, reference_model.right)
    initial_total = sum(s.initial_native_state.internal_energy_J
        +s.native_component.wall_heat_capacity*s.initial_native_state.wall_temperature_K for s in sides)

    def equilibrium_energy(temperature):
        total = 0.
        for side, eos in zip(sides, native_eos, strict=True):
            mass = side.initial_native_state.mass_kg
            eos.update(cp.DmassT_INPUTS, mass/side.native_component.fluid_volume, temperature)
            total += mass*eos.umass()+side.native_component.wall_heat_capacity*temperature
        return total-initial_total

    expected_equilibrium = brentq(equilibrium_energy, 250., 400., xtol=1e-10)
    equilibrium_error = max(abs(temperature-expected_equilibrium)
        for s in equilibrium_run.points[-1].sides.values()
        for temperature in (s.fluid.temperature_k, s.native_state.wall_temperature_K))

    independent = {"left": CoolPropProperties("Hydrogen"), "right": CoolPropProperties("ParaHydrogen")}
    independent_mass_error = independent_energy_error = 0.
    for p in fine.points:
        for name, side, volume, capacity in (("left", reference_model.left, .01, 100.),
                                             ("right", reference_model.right, .02, 150.)):
            observed = p.sides[name]
            native = independent[name].state_pt(observed.fluid.pressure_pa, observed.fluid.temperature_k)
            mass = volume*native.density_kg_m3
            energy = mass*native.internal_energy_j_kg+capacity*observed.native_state.wall_temperature_K
            initial_energy = side.initial_native_state.internal_energy_J+capacity*side.initial_native_state.wall_temperature_K
            independent_mass_error = max(independent_mass_error, abs(mass-side.initial_native_state.mass_kg))
            independent_energy_error = max(independent_energy_error,
                abs(energy-initial_energy-observed.balance.boundary_energy_j))
    sampled_errors = {name: float(np.trapezoid([p.sides[name].coupling_heat_into_side_w for p in fine.points],
        fine.time_s)-fine.points[-1].sides[name].balance.boundary_energy_j) for name in ("left", "right")}
    temperature_differences = [max(abs(temperature-other_temperature)
        for name in ("left", "right")
        for temperature, other_temperature in (
            (r.points[-1].sides[name].fluid.temperature_k, fine.points[-1].sides[name].fluid.temperature_k),
            (r.points[-1].sides[name].native_state.wall_temperature_K,
             fine.points[-1].sides[name].native_state.wall_temperature_K))) for r in (coarse, medium)]
    reverse_heat = [p.sides["left"].coupling_heat_into_side_w for p in reversed_heat.points]
    native_after = native_hash(native_directory)
    after_hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}
    gates = {
        "actual native cores, states, derivatives and one simultaneous integrator retained": all(
            isinstance(r.native_simulator, dynamic.DynamicNetworkSimulator)
            and all(isinstance(c, vaporizer.DynamicVaporizer) for c in r.native_components)
            and all(isinstance(s.native_state, vaporizer.DynamicVaporizerState)
                and isinstance(s.native_derivative, vaporizer.DynamicVaporizerDerivative)
                for p in r.points for s in p.sides.values()) for r in all_runs),
        "each sealed fluid mass remains fixed <1e-13 kg": max_mass < 1e-13,
        "each native fluid+wall energy defect <1e-5 J": max_side_energy < 1e-5,
        "closed pair global energy and integrated opposite heat <1e-5 J": max(max_global_energy, max_coupling) < 1e-5,
        "native heat rates equal/opposite <1e-9 W": max_opposite_rate < 1e-9,
        "both finite fluids and walls respond":
            fine.points[-1].sides["left"].fluid.temperature_k < 400.
            and fine.points[-1].sides["right"].fluid.temperature_k > 250.
            and fine.points[-1].sides["left"].native_state.wall_temperature_K < 400.
            and fine.points[-1].sides["right"].native_state.wall_temperature_K > 250.,
        "zero conductance gives independent stationary side inventories": all(
            zero.points[0].sides[name].inventory == zero.points[-1].sides[name].inventory for name in ("left", "right")),
        "independent analytic two-wall exponential <1e-8 K": analytic_wall_error < 1e-8,
        "fresh native fixed-density whole-system equilibrium <1e-5 K": equilibrium_error < 1e-5,
        "independent fresh native PT reconstructed side mass/U <1e-12 kg /1e-5 J":
            independent_mass_error < 1e-12 and independent_energy_error < 1e-5,
        "finite initial fluid/wall storage reverses interwall heat": min(reverse_heat) < -100. and max(reverse_heat) > 20.,
        "0.5/0.25/0.125 s final four-temperature agreement <1e-3 K": max(temperature_differences) < 1e-3,
        "finest accepted-sample independent heat quadrature <0.01 J": max(abs(v) for v in sampled_errors.values()) < .01,
        "separate normal/para bases retained without mass/reference mixing":
            fine.points[-1].sides["left"].fluid.basis.spin_composition == "normal"
            and fine.points[-1].sides["right"].fluid.basis.spin_composition == "para",
        "native and host/test/replay begin/end fingerprints unchanged":
            native_before == native_after and before_hashes == after_hashes,
    }
    elapsed = perf_counter()-started
    lines = ["# Native finite two-fluid heat exchanger", "",
        "Reproduce: `python scripts/check_heat_exchanger_integration.py` after installing the separately reviewed native snapshot.", "",
        f"Native LH2DT source `{REVISION}`, CoolProp {metadata.version('CoolProp')}, "
        f"SciPy {metadata.version('scipy')}; seven complete coupled integrations, {elapsed:.6g} s local calculation. "
        "Each uses one actual DynamicNetworkSimulator and two actual DynamicVaporizer cores/states/derivatives.", "",
        "Original synthetic closed case: left normal-H2 fluid 400 K /300000 Pa /0.01 m3, wall capacity 100 J/K, "
        "fluid-wall conductance 5 W/K; right para-H2 fluid 250 K /200000 Pa /0.02 m3, wall capacity 150 J/K, "
        "fluid-wall conductance 6 W/K. Each wall starts at its own fluid temperature. Both native ambient-UA slots "
        "are explicitly the same interwall conductance 2 W/K; each receives the other current finite wall temperature. "
        "No external bath, mass port or leakage is present. Each native fluid-wall heat cap is 1e6 W. "
        "The operating envelope is 200-650 K /1000-1e7 Pa /mass>1e-8 kg, and source clock starts 100 s. "
        "Coefficients are authored verification inputs, not manufacturer maps or experimental estimates.", "",
        "The public composite DynamicNodeModel advances both native states at every common RK stage. Native "
        "advance/combine and derivative_from_flows functions own all physical balances and heat laws. Only the "
        "per-side heat integrals are appended. A private port-free native scheduling network carries a left-side "
        "representative thermodynamic boundary for its API; it is not an aggregate exchanger pressure/state. "
        "The physical side bases and outputs remain separate. The native ambient heat field means internal "
        "counterpart-wall heat in this composition; its global sum is explicitly zero.", "",
        "| Quantity | Observed value |", "|---|---:|",
        *(f"| Fine {name} final fluid / wall T | {fine.points[-1].sides[name].fluid.temperature_k:.12g} / "
          f"{fine.points[-1].sides[name].native_state.wall_temperature_K:.12g} K |" for name in ("left", "right")),
        f"| Maximum side mass / energy defect | {max_mass:.12g} kg / {max_side_energy:.12g} J |",
        f"| Maximum global-U / opposite integrated heat defect | {max_global_energy:.12g} / {max_coupling:.12g} J |",
        f"| Maximum native opposite heat-rate defect | {max_opposite_rate:.12g} W |",
        f"| Independent analytic two-wall temperature error | {analytic_wall_error:.12g} K |",
        f"| Independent whole-system equilibrium / max final error | {expected_equilibrium:.12g} / {equilibrium_error:.12g} K |",
        f"| Fresh native PT mass / side-U defects | {independent_mass_error:.12g} kg / {independent_energy_error:.12g} J |",
        f"| Coarse/medium four-temperature differences from fine | {temperature_differences} K |",
        f"| Fine accepted-sample left/right heat errors | {sampled_errors} J |",
        f"| Reversal left-side heat range | {min(reverse_heat):.12g} to {max(reverse_heat):.12g} W |",
        f"| Fine actual stage clock bounds / pair derivative evaluations | {fine.evaluated_clock_bounds_s} s / {fine.native_evaluation_count} |", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "Numerical/interface verification is distinct from measured validation. The model has two spatially uniform "
        "finite fluids and two walls. It does not solve counterflow/parallel-flow profiles, LMTD/NTU effectiveness, "
        "hydraulic pressure drop, process-port flow, thermal leakage, variable conductance/isolation or a vendor rating. "
        "Different material energy zeros cause no hidden transfer: side masses are fixed and their energy changes "
        "are audited separately before summing. Native EOS/phase/domain and per-side closure failures propagate.", "",
        "Receiving work includes a native composite thermal-group boundary that does not need a representative "
        "hydraulic state, public heat-port separation from ambient fields, conservative process-port/leak ledgers, "
        "and accepted-step streaming hooks. Current trial evaluations are buffered then matched to actual accepted "
        "composite-state identity; no fixed RK call count is used for acceptance. No receiving repository is edited "
        "or messaged, and no external data/native code is bundled.", "",
        "Primary references: [native LH2DT](https://github.com/lyullee/lh2dt_models), "
        "[DOE heat-transfer fundamentals](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1012-92_VOL2.pdf), "
        "[CoolProp native EOS](https://doi.org/10.1021/ie4033999). Original composition, analytic cases and tests; "
        "no heat law, native ODE, EOS implementation or coefficient table was copied.", "",
        "## Begin/end fingerprints", "",
        f"- Native Python aggregate before: `{native_before}`",
        f"- Native Python aggregate after: `{native_after}`",
        *(f"- Native `{name}`: `{sha}`" for name, sha in native_files.items()),
        *(f"- `{name}`: `{sha}`" for name, sha in before_hashes.items()), "",
        "| Host source | Begin SHA-256 | End SHA-256 |", "|---|---|---|",
        *(f"| `{name}` | `{sha}` | `{after_hashes[name]}` |" for name, sha in before_hashes.items()), ""]
    (root/"research/native_heat_exchanger.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name, passed in gates.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"Local calculation: {elapsed:.6g} s; report: research/native_heat_exchanger.md")
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
